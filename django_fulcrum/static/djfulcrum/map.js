	/*
	Copyright 2016, RadiantBlue Technologies, Inc.

	Licensed under the Apache License, Version 2.0 (the "License");
	you may not use this file except in compliance with the License.
	You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

	Unless required by applicable law or agreed to in writing, software
	distributed under the License is distributed on an "AS IS" BASIS,
	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	See the License for the specific language governing permissions and
	limitations under the License.
	*/
	
"use strict";
		
	$(window).load(function () {
	
		if (!Date.now) {
				Date.now = function() { return new Date().getTime() } //Time in milliseconds
		}
		
		var baseMaps = {};

		var miniMaps = {};

		// Track which layers are in the map //
		var activeLayers = {};
		
		// Track layer colors for legend //
		var layerStyles = {};
		
		// Track refresh intervals sources for each layer //
		var layerUpdates = {};
		
		// Track layer sources //
		var layerUrls = {};
		
		// Empty layer list for any user uploaded layers //
		var layers = {};
		
		// Create divisions in the layer control //
		var overlays = {
			"Fulcrum Layers": layers,
		};

		for (var basemap in basemapInfo) {
    		var base = L.tileLayer(basemapInfo[basemap][1],{
    			minZoom : 0,
    			maxZoom : 18,
    			attribution : basemapInfo[basemap][2],
    		});
    		var mini = L.tileLayer(basemapInfo[basemap][1],{
    			minZoom : 0,
    			maxZoom : 16,
    			attribution : basemapInfo[basemap][2],
    		});
    		var name = basemapInfo[basemap][0];
    		baseMaps[name] = base;
    		miniMaps[name] = mini;
    	}

    	var map = L.map('map', {
			zoomControl: false,
			fullscreenControl: true,
			center:[0, 0], 
			zoom: 2,
			layers: baseMaps[basemapInfo[0][0]]
		});

		//Set starting bounds for zoom-to-extent button //
		var defaultBounds = map.getBounds();
		var north = -90.0;
		var east = -180.0;
		var south = 90.0;
		var west = 180.0;
		var bounds = defaultBounds;
		
		// Get the bounds of a layer and compare to any other active layers //
		function fetchBounds(layer) {
			var temp = L.latLngBounds(layer.getBounds()); 
			north = (north > temp.getNorth() ? north : temp.getNorth());
			east = (east > temp.getEast() ? east : temp.getEast());
			south = (south < temp.getSouth() ? south : temp.getSouth());
			west = (west < temp.getWest() ? west : temp.getWest());
			var SW = L.latLng(south,west)
			var NE = L.latLng(north,east);
			return L.latLngBounds(SW, NE);
		};
		
		var layerControl;
		
		// Gets list of available layers //
		$.ajax({
			url : '/fulcrum_layers',
			dataType: "json",
			success : function(result) {
				updateLayers(result, true);
			}
		});
		
		setInterval(function(){
			$.ajax({
				url : '/fulcrum_layers',
				dataType: "json",
				success : function(result) {
					//layerControl.removeFrom(map);
					//layerControl = null;
					updateLayers(result, false);
				}
			});
		}, 30000);
		
		// Update the layer control with any new layers //
		function updateLayers(result, firstcall) {
			for (var key in result) {
				if(!(key in layers)){
					if(!(key in layerStyles)) {
						var color = getRandomColor();
						layerStyles[key] = {
							radius : 4,
							fillColor : color,
							color : "#000000",
							weight : 1, 
							opacity : 1,
							fillOpacity : 1
						}
					};
					layers[key] = L.geoJson(false);
					layerUrls[key] = '/fulcrum_geojson?layer=' + key;
					console.log(layerUrls[key]);
					if (firstcall == false) {
						layerControl.addOverlay(layers[key], key, "Fulcrum Layers");
					}
				}
			}
			if (firstcall == true) {
				layerControl = L.control.groupedLayers(baseMaps, overlays).addTo(map);
			}
		};
		
		// Listens for user selecting a layer from Layer Control //
		map.on('overlayadd', onOverlayAdd);

		// Find which layer was selected, get its data from URL, add it to the empty layer, and add the layer to the map //
		function onOverlayAdd(e) {
			var name = e["name"];
			console.log("Going to get: " + layerUrls[name]);
			$.ajax({
					url : layerUrls[name],
					dataType: "json",
					success : function(result) {
						addSuccess(result, name);
					}, 
			});
		};
		
		function addSuccess(result, name) {
			var layer = result[name];
			addLayer(layer, name);
			activeLayers[name] = null;
			bounds = fetchBounds(layers[name]);
			// If no layers/legend currently: add legend, else: delete old version and add new version //
			if(Object.keys(activeLayers).length == 1) {
				legend.addTo(map);
			}
			else {
				legend.removeFrom(map);
				legend.addTo(map);
			}
			layerRefresher(name);
		};
		
		function addLayer(layer, name) {
			console.log("Adding layer");
			console.log(layer);
			layers[name] = L.geoJson(layer, {
				onEachFeature: onEachFeature,
				filter : function(feature) {
					if (timeout != 0) {
						return feature.properties.time + (timeout * 60) > Math.floor(Date.now()/1000);
					}
					else {
						return true;
					}
				},
				pointToLayer: function(feature, latlng) {
					return L.circleMarker(latlng, Markers(feature, name));
				}
			}).addTo(map);
		};
		
		function layerRefresher(key) {
			layerUpdates[key] = setInterval(function() {
				console.log("Updating");
				$.ajax({
						url : layerUrls[key],
						dataType: "json",
						success : function(result) {
							var layer = result[key];
							layers[key].clearLayers();
							layers[key] = null;
							addLayer(layer, key);
							north = -90.0;
							east = -180.0;
							south = 90.0;
							west = 180.0;
							bounds = defaultBounds;
							bounds = fetchBounds(layers[key]);
						}, 
					});
			}, refresh * 1000);
		};
		
		// Listens for user deselecting layer from Layer Control //
		map.on('overlayremove', onOverlayRemove);
		
		// Removes layer data from the geojson layer //
		function onOverlayRemove(e) {
			var name = e["name"];
			console.log("Updates stopped");
			clearInterval(layerUpdates[name]);
			layerUpdates[name] = null;
			layers[name].clearLayers();
			layers[name] = null;
			delete activeLayers[name];
			// Reset bounds then iterate through any active layers to compute new bounds //
			north = -90.0;
			east = -180.0;
			south = 90.0;
			west = 180.0;
			bounds = defaultBounds;
			for (var key in activeLayers) {
				if (key in layers) {
					bounds = fetchBounds(layers[key]);
				}
			}
			// If removing only layer: remove legend, else: remove and add new version //
			legend.removeFrom(map);
			if(Object.keys(activeLayers).length != 0) {
				legend.addTo(map);
			};
		};
		
		// Create legend for active layers //
		var legend = L.control({position: 'bottomright'});

		legend.onAdd = function (map) {
			var div = L.DomUtil.create('div', 'legend');
			for(var key in activeLayers) {
				div.innerHTML +=
					'<div class="subdiv">' +
					'<i class="circle" style="background: '+ layerStyles[key].fillColor + '"></i> ' +
					'<span class="legend-lable">' + key + '</span><br>'
					+ '</div>';
			}
			return div;
		};
		
		// Adds a locator map to bottom corner of the main map //
		var miniMap = new L.Control.MiniMap(miniMaps[basemapInfo[0][0]]).addTo(map);
		
		map.on('baselayerchange', function(e) {
			var base = e["name"];
			miniMap.removeFrom(map);
			miniMap = new L.Control.MiniMap(miniMaps[base]).addTo(map);
		});
		
		// Adds a popup with information for each point //
		function onEachFeature(feature, layer) {
			layer.on('click', function (e) {
				var genericStr = "";
				var titleStr = "";
				var idStr = "";
				var photosStr = "";
				var audioStr = "";
				var videosStr = "";
				for (var property in e.target.feature.properties) {
					
					if (String(property).toLowerCase().indexOf('name') > -1 || String(property).toLowerCase().indexOf('title') > -1) {
						titleStr += '<p><strong>' + property + ':</strong> ' + e.target.feature.properties[property] + '</p>'
					}
					else if (String(property).toLowerCase().indexOf('id') == 0){
						idStr += '<p><strong>' + property + ':</strong> ' + e.target.feature.properties[property] + '</p>'
					}
					else if(String(property).indexOf('_url') > -1) {
						if (e.target.feature.properties[property] != null && e.target.feature.properties[property] != "") {
							var urls = String(e.target.feature.properties[property]).split(",");
							console.log(urls);
							for (var url in urls){
								if(String(urls[url]).indexOf('.jpg') > -1) {
									photosStr += '<p><a href="' + urls[url] + '" target="_blank"><img src="' + urls[url] + '" style="width: 250px; height: 250px;"/></a></p>';
								}
								if(String(urls[url]).indexOf('.mp4') > -1) {
									videosStr += '<p><video width="250" height="250" controls><source src="' + urls[url] + '" type="video/mp4" target="_blank"></video></p>';
								}
								if(String(urls[url]).indexOf('.m4a') > -1) {
									audioStr += '<p><audio controls><source src="' + urls[url] + '" type="audio/mp4"></audio></p>';
								}
							}
						}
					}
					else {
						if (e.target.feature.properties[property] != null && e.target.feature.properties[property] != "") {
							genericStr += '<p><strong>' + property + ':</strong> ' + e.target.feature.properties[property] + '</p>';
						}
					}
				}
				
				// Get position for popup //
				var coords = [e.target.feature.geometry.coordinates[1],e.target.feature.geometry.coordinates[0]];
				
				// Create popup and add to map //
				var popup = L.popup({
					maxHeight: 400,
					closeOnClick: false,
					keepInView: true
				}).setLatLng(coords).setContent(titleStr + idStr + genericStr + photosStr + videosStr + audioStr).openOn(map);
			});
		}
		
		// Symbolizes new points in red, old points in grey //
		function Markers (feature, key) {
			
			
			if (feature.properties.time + (colortime * 60) > Math.round(Date.now()/1000.0) && colortime > 0){
				return {
					radius : 5,
					fillColor : "#e60000",
					color : "#000000",
					weight : 1,
					opacity : 1,
					fillOpacity : 1
				}
			}
			
			else {
			    return layerStyles[key];
			}
		}
		
		
		// Show coordinates of mouse position //
		L.control.mousePosition().addTo(map);
		
		// Option to get your own location on the map //
		L.control.locate({
			position: 'topleft',
			drawCircle: false,
			remainActive: false,
			icon: 'fa fa-map-marker'
		}).addTo(map);
		
		// Adds a return to home extend button //
		var zoomHome = L.Control.zoomHome();
		zoomHome.addTo(map);
		
		// Adds numeric scale to map //
		L.control.scale().addTo(map);
		
		// Button to fit map extent to bounds of point layer //
		var extentButton = L.easyButton({
			states: [{
				stateName: 'Zoom to extent of current features',
				icon: 'fa-map',	
				title: 'Zoom to extent of current features',
				onClick: function(btn, map) {
					map.fitBounds(bounds);
				}
			}]
		}).addTo(map);
		
		// Adds draggable zoom box //
		var zoomBox = L.control.zoomBox({
			className: 'fa fa-search-plus',
			modal: true,
		}).addTo(map);
		
		
		// Button to set alert timeout //
		if(typeof(Storage) != "undefined") {
			if (sessionStorage.timeout) {
				var timeout = parseInt(sessionStorage.timeout);
			}
			else {
				sessionStorage.timeout = "0";
				timeout = 0;
			}
		}
		else {
			var timeout = 0;
		}
		document.getElementById("timeout").value = timeout;
		var getTimeout = $(function() {
		
			var TimeDialogBox = $("#timeoutForm").dialog({
				autoOpen: false,
				closeOnEscape: false,
				open: function(event, ui) {
					$(".ui-dialog-titlebar-close", ui.dialog | ui).hide();
					$("#colortimeForm").dialog('close');
					$("#refreshForm").dialog('close');
					$("#subscribeForm").dialog('close');
					$("#formContainer").dialog('close');
					$("#pzContainer").dialog('close');
					$("#triggerContainer").dialog('close');
					$("#eventContainer").dialog('close');
					$("#alertContainer").dialog('close');
				},
				height: 250,
				width: 350,
				appendTo: "#map",
				position: {
					my: "left top",
					at: "right bottom",
					of: placeholder
				},
				modal: false,
				buttons: {
					"Submit": function() {
						var inNum = parseInt($("#timeout").val());
						if(isNaN(inNum) || inNum < 0 || inNum == "") {
							timeout = 0;
							document.getElementById("timeout").value = timeout;
							sessionStorage.timeout = timeout;
						}
						else {
							timeout = inNum;
							sessionStorage.timeout = inNum;
							
						}
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					},
					"Cancel": function() {
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					}
				},
			
			});
			
			$('#timeoutForm').keypress( function(e) {
				if (e.charCode == 13 || e.keyCode == 13) {
					var inNum = parseInt($("#timeout").val());
						if(isNaN(inNum) || inNum < 0 || inNum == "") {
							timeout = 0;
							document.getElementById("timeout").value = timeout;
							sessionStorage.timeout = timeout;
						}
						else {
							timeout = inNum;
							sessionStorage.timeout = inNum;
						}
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					e.preventDefault();
				}
			});
			
			var timeoutButton = L.easyButton({
				states: [{
					stateName: 'Set timeout for features',
					icon: 'fa-clock-o',	
					title: 'Set timeout for features',
					onClick: function(btn, map) {
						map.dragging.disable();
						map.doubleClickZoom.disable();
						TimeDialogBox.dialog("open");
					}
				}]
			}).addTo(map);
		});		
	
		
		// Button to set new alert color time //
		if(typeof(Storage) != "undefined") {
			if (sessionStorage.colortime) {
				var colortime = parseInt(sessionStorage.colortime);
			}
			else {
				sessionStorage.colortime = "0";
				colortime = 0;
			}
		}
		else {
			var colortime = 0;
		}
		document.getElementById("colortime").value = colortime;
		var getColortime = $(function() {
		
			var colorDialogBox = $("#colortimeForm").dialog({
				autoOpen: false,
				closeOnEscape: false,
				open: function(event, ui) {
					$(".ui-dialog-titlebar-close", ui.dialog | ui).hide(); 
					$("#timeoutForm").dialog('close');
					$("#refreshForm").dialog('close');
					$("#subscribeForm").dialog('close');
					$("#formContainer").dialog('close');
					$("#pzContainer").dialog('close');
					$("#triggerContainer").dialog('close');
					$("#eventContainer").dialog('close');
					$("#alertContainer").dialog('close');
				},
				height: 250,
				width: 350,
				appendTo: "#map",
				position: {
					my: "left top",
					at: "right bottom",
					of: placeholder
				},
				modal: false,
				buttons: {
					"Submit": function() {
						var inNum = parseInt($("#colortime").val());
						if(isNaN(inNum) || inNum < 0 || inNum == '') {
							colortime = 0;
							document.getElementById("colortime").value = colortime;
							sessionStorage.colortime = colortime;
						}
						else {
							colortime = inNum;
							sessionStorage.colortime = inNum;
						}
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					},
					"Cancel": function() {
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					}
				},
			
			});
			
			$('#colortimeForm').keypress( function(e) {
				if (e.charCode == 13 || e.keyCode == 13) {
					var inNum = parseInt($("#colortime").val());
						if(isNaN(inNum) || inNum < 0 || inNum == "") {
							colortime = 0;
							document.getElementById("colortime").value = colortime;
							sessionStorage.colortime = colortime;
						}
						else {
							colortime = inNum;
							sessionStorage.colortime = inNum;
						}
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					e.preventDefault();
				}
			});
			
			var colorTimeButton = L.easyButton({
				states: [{
					stateName: 'Set time for new feature color',
					icon: 'fa-eye',	
					title: 'Set time for new feature color',
					onClick: function(btn, map) {
						map.dragging.disable();
						map.doubleClickZoom.disable();
						colorDialogBox.dialog("open");
					}
				}]
			}).addTo(map);
		});
		
		// Button to set new Refresh rate //
		var refresh;
		if(typeof(Storage) != "undefined") {
			if (sessionStorage.refresh) {
				refresh = parseInt(sessionStorage.refresh);
			}
			else {
				sessionStorage.refresh = "60";
				refresh = 60;
			}
		}
		else {
			refresh = 60;
		}
		document.getElementById("refresh").value = refresh;
		var getRefresh = $(function() {
		
			var refreshDialogBox = $("#refreshForm").dialog({
				autoOpen: false,
				closeOnEscape: false,
				open: function(event, ui) {
					$(".ui-dialog-titlebar-close", ui.dialog | ui).hide();
					$("#timeoutForm").dialog('close');
					$("#colortimeForm").dialog('close');
					$("#subscribeForm").dialog('close');
					$("#formContainer").dialog('close');
					$("#pzContainer").dialog('close');
					$("#triggerContainer").dialog('close');
					$("#eventContainer").dialog('close');
					$("#alertContainer").dialog('close');
				},
				height: 250,
				width: 350,
				appendTo: "#map",
				position: {
					my: "left top",
					at: "right bottom",
					of: placeholder
				},
				modal: false,
				buttons: {
					"Submit": function() {
						var inNum = parseInt($("#refresh").val());
						if(isNaN(inNum) || inNum <= 0 || inNum == "") {
							refresh = 60;
							document.getElementById("refresh").value = refresh;
							sessionStorage.refresh = refresh;
						}
						else {
							refresh = inNum;
							sessionStorage.refresh = inNum;
							
						}
						for(var key in activeLayers) {
							clearInterval(layerUpdates[key]);
							layerUpdates[key] = null;
							layerRefresher(key);
						}
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					},
					"Cancel": function() {
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					}
				},
			
			});
			
			$('#refreshForm').keypress( function(e) {
				if (e.charCode == 13 || e.keyCode == 13) {
					var inNum = parseInt($("#refresh").val());
						if(isNaN(inNum) || inNum < 0 || inNum == "") {
							refresh = 60;
							document.getElementById("refresh").value = refresh;
							sessionStorage.refresh = refresh;
						}
						else {
							refresh = inNum;
							sessionStorage.refresh = inNum;
						}
						for(var key in activeLayers) {
							clearInterval(layerUpdates[key]);
							layerUpdates[key] = null;
							layerRefresher(key);
						}
						map.dragging.enable();
						map.doubleClickZoom.enable();
						$(this).dialog("close");
					e.preventDefault();
				}
			});
			
			var refreshButton = L.easyButton({
				states: [{
					stateName: 'Set time for layer refresh',
					icon: 'fa-refresh',	
					title: 'Set time for layer refresh',
					onClick: function(btn, map) {
						map.dragging.disable();
						map.doubleClickZoom.disable();
						refreshDialogBox.dialog("open");
					}
				}]
			}).addTo(map);
		});
		
		// Uploads user data //
		var uploadForm = (function(){
			map.dragging.enable();
			map.doubleClickZoom.enable();
			if ($('#uploadFormButton').val() != '' && $('#uploadFormButton').val() != null) {
				var formData = new FormData($('#fileUpload')[0]);
	            $.ajax({
	                url: '/fulcrum_upload',  //Server script to process data
	                type: 'POST',
	                xhr: function() {  // Custom XMLHttpRequest
	                    var myXhr = $.ajaxSettings.xhr();
	                    if(myXhr.upload){ // Check if upload property exists
	                        myXhr.upload.addEventListener('progress',progressHandlingFunction, false); // For handling the progress of the upload
							myXhr.upload.addEventListener('progress',progressFinishedFunction, false); // If progress is finished, close file upload dialog
	                    }
	                    return myXhr;
	                },
	                // Ajax events //
	                beforeSend: console.log("Sending"),
					// Adds layer to the map //
	                success: function (result) {
						document.getElementById('waiting').style.visibility = 'hidden';
						for(var key in result) {
							// If layer already exists, remove first, then add new version //
							if(key in layers) {
								map.removeLayer(layers[key]);
								layerControl.removeLayer(key);
								delete layers[key];
								if(key in activeLayers) {
									delete activeLayers[key];
								};
							}
							layerControl.removeFrom(map);
							updateLayers(result);
							
						};
						
					},
	                error: console.log("Fail"),
	                // Form data //
	                data: formData,
	                // Options to tell jQuery not to process data or worry about content-type. //
	                cache: false,
	                contentType: false,
	                processData: false
	            });
			}
			else {
				console.log("No file selected");
			}
        });
        
		// For progress bar ..
        function progressHandlingFunction(e){
            if(e.lengthComputable){
                $('progress').attr({value:e.loaded,max:e.total});
            }
        }
		function progressFinishedFunction(e) {
			if(e.lengthComputable){
				if(e.loaded == e.total) {
					$("#formContainer").dialog("close");
					$('progress').attr({value: 0.0, max: 1.0});
					document.getElementById('waiting').style.visibility = 'visible';
				}
			}
		}
		
		// Upload dialog box //
		var uploadFileDialogBox = $("#formContainer").dialog({
			autoOpen: false,
			closeOnEscape: false,
			open: function(event, ui) {
				$(".ui-dialog-titlebar-close", ui.dialog | ui).hide(); 
				$("#timeoutForm").dialog('close');
				$("#colortimeForm").dialog('close');
				$("#refreshForm").dialog('close');
				$("#subscribeForm").dialog('close');
				$("#pzContainer").dialog('close');
				$("#triggerContainer").dialog('close');
				$("#eventContainer").dialog('close');
				$("#alertContainer").dialog('close');
			},
			height: 250,
			width: 500,
			appendTo: "#map",
			position: {
				my: "left top",
				at: "right bottom",
				of: placeholder
			},
			modal: true,
			buttons: {
				"Upload": uploadForm,
				"Cancel": function() {
					map.dragging.enable();
					map.doubleClickZoom.enable();
					$(this).dialog("close");
				}
			},
		});
         
		// Button to call upload dialog box //
        var uploadFileButton = L.easyButton({
			states: [{
				stateName: 'Upload File',
				icon: 'fa fa-upload',	
				title: 'Upload File',
				onClick: function(btn, map) {
					map.dragging.disable();
					map.doubleClickZoom.disable();
					uploadFileDialogBox.dialog("open");
				}
			}]
		}).addTo(map);
		
		// Handles use of enter key //
        $('#fileUpload').keypress( function(e) {
			if (e.charCode == 13 || e.keyCode == 13) {
				uploadForm();
				map.dragging.enable();
				map.doubleClickZoom.enable();
				e.preventDefault();
				
			}
		});
		
		function getCookie(name) {
				var cookieValue = null;
				if (document.cookie && document.cookie != '') {
					var cookies = document.cookie.split(';');
						for (var i = 0; i < cookies.length; i++) {
							var cookie = jQuery.trim(cookies[i]);
							// Does this cookie string begin with the name we want?
							if (cookie.substring(0, name.length + 1) == (name + '=')) {
								cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
								break;
							}
						}
				}
				return cookieValue;
			}
			
		function csrfSafeMethod(method) {
			// these HTTP methods do not require CSRF protection
			return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
		}
	
		// Gets randomized color for new layer //
		var approvedColors = [
			"#0000ff",
			"#a52a2a",
			"#00ffff",
			"#00008b",
			"#008b8b",
			"#a9a9a9",
			"#006400",
			"#bdb76b",
			"#8b008b",
			"#556b2f",
			"#ff8c00",
			"#9932cc",
			"#e9967a",
			"#9400d3",
			"#ff00ff",
			"#ffd700",
			"#008000",
			"#4b0082",
			"#f0e68c",
			"#add8e6",
			"#e0ffff",
			"#90ee90",
			"#d3d3d3",
			"#ffb6c1",
			"#ffffe0",
			"#00ff00",
			"#ff00ff",
			"#800000",
			"#000080",
			"#808000",
			"#ffa500",
			"#ffc0cb",
			"#800080",
			"#800080",
			"#c0c0c0",
			"#ffff00"
		]
		var colorix = 0;
		function getRandomColor() {
			if(colorix < approvedColors.length) {
				console.log(approvedColors[colorix]);
				return approvedColors[colorix++];
			}
			else {
				colorix = 1;
				console.log(approvedColors[colorix]);
				return approvedColors[0];
			}
		};
		
		String.prototype.format = function() {
			var formatted = this;
			for (var i = 0; i < arguments.length; i++) {
				var regexp = new RegExp('\\{'+i+'\\}', 'gi');
				formatted = formatted.replace(regexp, arguments[i]);
			}
			return formatted;
		};
	});
