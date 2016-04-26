# Copyright 2016, RadiantBlue Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from django.contrib import admin
from .models import S3Credential, S3Bucket, FulcrumApiKey, Filter, FilterGeneric, FilterArea
from django.contrib import messages
from django.contrib.admin import helpers
from django.template.response import TemplateResponse


class S3BucketInline(admin.TabularInline):
    model = S3Bucket


class S3Admin(admin.ModelAdmin):
    inlines = [
        S3BucketInline
    ]

    fieldsets = (
        (None, {
            'fields': ('s3_description', 's3_key', 's3_secret', 's3_gpg'),
            'description': "Enter S3 Credentials for a bucket(s) which contain one or more zipfiles of Fulcrum data."
        }),
    )


class FilterGenericInline(admin.TabularInline):
    model = FilterGeneric
    can_delete = True


class FilterAreaInline(FilterGenericInline):
    model = FilterArea
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('filter_area_enabled',
                       'filter_area_name',
                       'filter_area_buffer',
                       'filter_area_data'),
            'description': "Data can be excluded through filters or included."
        }),
    )


class FilterAdmin(admin.ModelAdmin):
    actions = None
    readonly_fields = ('filter_name', 'filter_previous_status')
    exclude = ('filter_previous_time',)
    model = Filter
    fieldsets = (
        (None, {
            'fields': ('filter_name',
                       'filter_active',
                       'filter_inclusion',
                       'filter_previous',
                       'filter_previous_status',),
            'description': "Filters are DESTRUCTIVE, points cannot be recovered if filtered.  "
                           "Filters are applied to ALL layers."
        }),
    )

    def has_add_permission(self, request):
        return False

    def response_post_save_change(self, request, obj):
        from django.http import HttpResponseRedirect
        from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
        from django.core.urlresolvers import reverse
        from django.template.loader import get_template
        from django.template.response import TemplateResponse

        if request.POST.get('filter_previous') and request.POST.get('filter_previous') == 'on':
            if request.POST.get('post'):
                opts = self.model._meta

                if self.has_change_permission(request, None):
                    post_url = reverse('admin:{}_{}_changelist'.format(opts.app_label, opts.model_name),
                                       current_app=self.admin_site.name)
                    preserved_filters = self.get_preserved_filters(request)
                    post_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, post_url)
                else:
                    post_url = reverse('admin:index',
                                       current_app=self.admin_site.name)
                return HttpResponseRedirect(post_url)

            if not request.POST.get('post'):
                context = {
                    'title': "Filter Previous Confirmation",
                    'formset': request.POST,
                    'request': request,
                }
                confirmation_page = get_template('djfulcrum/confirmation.html')
                return TemplateResponse(request, confirmation_page, context, current_app=self.admin_site.name)
        else:
            opts = self.model._meta

            if self.has_change_permission(request, None):
                post_url = reverse('admin:{}_{}_changelist'.format(opts.app_label, opts.model_name),
                                   current_app=self.admin_site.name)
                preserved_filters = self.get_preserved_filters(request)
                post_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, post_url)
            else:
                post_url = reverse('admin:index',
                                   current_app=self.admin_site.name)
            return HttpResponseRedirect(post_url)

    def save_model(self, request, obj, form, change):
        if obj.is_filter_running():
            messages.error(request, "The filter settings cannot be changed while filtering is in progress. \n"
                                    "The current changes have not been saved.")
        else:
            if not request.POST.get('filter_previous'):
                super(FilterAdmin, self).save_model(request, obj, form, change)

            elif request.POST.get('post') and request.POST.get('post') == 'Yes':
                super(FilterAdmin, self).save_model(request, obj, form, change)
            elif request.POST.get('post') and request.POST.get('post') == 'No':
                print "You did not confirm, not saving model"
            else:
                print "Waiting for confirmation"

    def save_formset(self, request, form, formset, change):
        if request.POST.get('post') and request.POST.get('post') == 'Yes':
            formset.save()
        elif not request.POST.get('filter_previous'):
            formset.save()

    def construct_change_message(self, request, form, formsets, add=False):
        from django.utils.encoding import force_text
        from django.utils.text import get_text_list
        from django.utils.translation import ugettext as _
        if (request.POST.get('post') and request.POST.get('post') == 'Yes') or not request.POST.get('filter_previous'):
            print "Creating change message"
            change_message = []
            if add:
                change_message.append(_('Added.'))
            elif form.changed_data:
                change_message.append(_('Changed {}.'.format(get_text_list(form.changed_data, _('and')))))

            if formsets:
                for formset in formsets:
                    for added_object in formset.new_objects:
                        change_message.append(
                                _('Added {name} "{object}".'.format(name=force_text(added_object._meta.verbose_name),
                                                                    object=force_text(added_object))))
                    for changed_object, changed_fields in formset.changed_objects:
                        change_message.append(_(
                                'Changed {list} for {name} "{object}"'.format(
                                    list=get_text_list(changed_fields, _('and')),
                                    name=force_text(
                                            changed_object._meta.verbose_name),
                                    object=force_text(changed_object))))
                    for deleted_object in formset.deleted_objects:
                        change_message.append(
                                _('Deleted {name} "{object}".'.format(
                                    name=force_text(deleted_object._meta.verbose_name),
                                    object=force_text(deleted_object))))
            change_message = ' '.join(change_message)
            return change_message or _('No fields changed.')
        else:
            print "Not creating change message"
            return _('No fields changed.')

    def get_inline_instances(self, request, obj=None):
        inline_instances = []

        if obj.filter_name == 'geospatial_filter.py':
            inlines = [FilterAreaInline]
        else:
            inlines = []

        for inline_class in inlines:
            inline = inline_class(self.model, self.admin_site)
            if request:
                if not (inline.has_add_permission(request) or
                            inline.has_change_permission(request) or
                            inline.has_delete_permission(request)):
                    continue
                if not inline.has_add_permission(request):
                    inline.max_num = 0
            inline_instances.append(inline)
        return inline_instances

    def get_formsets(self, request, obj=None):
        for inline in self.get_inline_instances(request, obj):
            yield inline.get_formset(request, obj)


admin.site.register(S3Credential, S3Admin)
admin.site.register(FulcrumApiKey)
admin.site.register(Filter, FilterAdmin)
