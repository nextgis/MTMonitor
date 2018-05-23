# coding=utf-8

#==============================================================================
#title           :MTMonitor.py
#description     :Class providing interface to MarineTraffic.com API (PS05 and PS06)
#author          :ekazakov (silenteddie@gmail.com)
#date            :2018.04
#version         :0.1
#usage           :see on github
#notes           :
#python_version  :2.7
#==============================================================================

import random
import time
import os
import json
from datetime import datetime
import requests
from requests.compat import urljoin
from pyproj import Proj, transform
import shapely
from shapely.geometry import Polygon
from shapely.geometry import Point
from shapely.geometry import mapping
import fiona
from fiona.crs import from_epsg
from MT_NGW_init_schemes import MT_NGW_init_schemes

class MTMonitor():

    MT_API_Key = ''
    MT_API_gate = 'https://services.marinetraffic.com/api/exportvessels/v:8'
    default_time_period = 5 # In minutes
    default_run_period = 5  # In minutes
    monitoring_areas = []
    last_vessels_response = []

    def __init__(self, MT_API_Key, mode='Predefined', monitoring_area_source=None):
        """
        Class initialization.
        Inputs are MarineTraffic API Key, mode and (optionally) OGR source with region of interest
        Modes are:

        1. Predefined - For PS05 API Service
        https://www.marinetraffic.com/ru/ais-api-services/detail/ps05/vessel-positions-in-a-predefined-area/

        2. Custom - For PS06 API Service
        https://www.marinetraffic.com/ru/ais-api-services/detail/ps06/vessel-positions-in-a-custom-area/

        OGR source could be any type supported by Fiona lib:
        'ESRI Shapefile', 'MapInfo File', 'GeoJSON', 'PDS', 'FileGDB',
        'GPX', 'DXF', 'GMT', 'GPKG', 'BNA', 'GPSTrackMaker'
        Allowed any SRS with epsg code.

        If monitoring area OGR source specified, all vessels will be filtered by it.

        :param mode: Mode for interacting with MarineTraffic
        :type mode: str

        :param monitoring_area_source: Source for input geodata
        :type monitoring_area_source: str

        :param MT_API_Key: API Key for MarineTraffic.com API Service
        :type MT_API_Key: str
        """

        self.MT_API_Key = MT_API_Key

        if mode not in ['Predefined','Custom']:
            print 'Invalid mode. Valid options are: Predefined, Custom. Auto set to Predefined'
            self.mode = 'Predefined'
        else:
            self.mode = mode

        if monitoring_area_source:
            source_dataset = fiona.open(monitoring_area_source)

            source_epsg = source_dataset.crs['init']

            if str(source_epsg).lower() != 'epsg:4326':
                monitoring_area_full_shapes = self.__get_reprojected_vector_dataset_coordinates(source_dataset, source_epsg, 'epsg:4326')
            else:
                monitoring_area_full_shapes = self.__get_raw_vector_dataset_coordinates(source_dataset)

            for feature in monitoring_area_full_shapes:
                self.monitoring_areas.append({'geometry':feature,'bounds':self.__get_bounds_from_coordinates(feature)})


    def get_vessels(self, time_period=None, emulation=False):
        """
        Interaction with MarineTraffic API

        Performing request with defined during initialization Mode and API Key.
        If emulation is True, random vessels generated

        :param emulation: Generate vessels without interacting with API (for tests)
        :type emulation: bool

        :param time_period: Time to observe vessels in minutes
        :type time_period: int

        :return: filtered list of vessels as list of dicts
        """

        request_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        vessels_filtered = []
        if not time_period:
            time_period = self.default_time_period

        ##### EMULATION FOR TESTS

        if emulation:
            vessels = []
            for i in range(0,10,1):
                x = random.uniform (58.3209,59.6744)
                y = random.uniform(68.9573, 69.544)
                vessel = {"MMSI":"304010417","IMO":"9015462","SHIP_ID":"359396","LAT":str(y),"LON":str(x),"SPEED":"74","HEADING":"329","COURSE":"327","STATUS":"0","TIMESTAMP":"2017-05-19T09:39:57","DSRC":"TER","UTC_SECONDS":"54"}
                vessels.append(vessel)

            if self.monitoring_areas:
                for area in self.monitoring_areas:
                    #print 'Vessels:'
                    #print vessels
                    for vessel in vessels:
                        if self.__point_inside_polygon(float(vessel['LON']), float(vessel['LAT']), area['geometry']):
                            vessels_filtered.append(vessel)
            else:
                vessels_filtered = vessels

        ##### END EMULATION

        else:

            if self.mode == 'Predefined':
                vessels = self.__marine_traffic_vp_in_predifined_area_request(time_period)
                print vessels
                if self.monitoring_areas:
                    for area in self.monitoring_areas:
                        #print 'Vessels:'
                        #print vessels
                        for vessel in vessels:
                            if self.__point_inside_polygon(float(vessel['LON']), float(vessel['LAT']), area['geometry']):
                                vessels_filtered.append(vessel)
                else:
                    vessels_filtered = vessels

            elif self.mode == 'Custom':
                if not self.monitoring_areas:
                    print 'Monitoring area must be specified. Provide it with option monitoring_area_source while' \
                          'class object initialization'
                    return vessels_filtered
                else:
                    for area in self.monitoring_areas:
                        vessels = self.__marine_traffic_vp_in_custom_area_request(time_period,
                                                                           area['bounds']['y_min'],
                                                                           area['bounds']['y_max'],
                                                                           area['bounds']['x_min'],
                                                                           area['bounds']['x_max'])
                        for vessel in vessels:
                            if self.__point_inside_polygon(float(vessel['LON']), float(vessel['LAT']), area['geometry']):
                                vessels_filtered.append(vessel)




        # Writing attributes NEW for new vessels and REQUEST_TIME
        print vessels_filtered
        for vessel_new_response in vessels_filtered:
            vessel_new_response['REQUEST_TIME'] = request_time
            vessel_new_response['NEW'] = True
            for vessel_last_response in self.last_vessels_response:
                if vessel_new_response['SHIP_ID'] == vessel_last_response['SHIP_ID']:
                    vessel_new_response['NEW'] = False

        self.last_vessels_response = vessels_filtered
        return vessels_filtered

    def export_vessels_to_file (self, output_file, output_type='GeoJSON', write_mode='new'):
        """
        Exporting result of last get_vessels call to vector file

        output_type could be any type supported by Fiona lib:
        'ESRI Shapefile', 'MapInfo File', 'GeoJSON', 'PDS', 'FileGDB',
        'GPX', 'DXF', 'GMT', 'GPKG', 'BNA', 'GPSTrackMaker'

        write_mode could be one of:
        1. new - new file will be created
        2. rewrite - existing file will be rewrited
        (for manual call 1 and 2 are equal)
        3. append - append new vessels to existing file

        :param output_file: Path to output file
        :type output_file: str

        :param output_type: Type of output file
        :type output_type: str

        :param write_mode: Exporting mode
        :type write_mode: str
        """

        output_schema = {'geometry': 'Point',
                         'properties': {'LAT': 'str',
                                        'LON': 'str',
                                        'SHIP_ID': 'str',
                                        'MMSI': 'str',
                                        'IMO': 'str',
                                        'SPEED': 'str',
                                        'HEADING': 'str',
                                        'COURSE': 'str',
                                        'STATUS': 'str',
                                        'TIMESTAMP': 'str',
                                        'DSRC': 'str',
                                        'UTC_SECONDS':'str',
                                        'NEW': 'str',
                                        'REQUEST_TIME': 'str'}}

        if (not os.path.exists(output_file)) or (write_mode == 'new') or (write_mode == 'rewrite'):
            if os.path.exists(output_file):
                os.remove(output_file)

            output = fiona.open(output_file, 'w', driver=output_type, schema=output_schema, crs=from_epsg(4326))

        elif write_mode == 'append':
            input = fiona.open(output_file,'r')
            input_schema = input.schema.copy()
            input_driver = input.driver
            features = list(input.items())
            input.close()
            os.remove(output_file)
            output = fiona.open(output_file, 'w', driver=input_driver, schema=input_schema, crs=from_epsg(4326))
            for feature in features:
                output.write(feature[1])
        else:
            print 'unsupported mode'
            return

        for vessel in self.last_vessels_response:
            # print vessel
            coordinate = Point(float(vessel['LON']), float(vessel['LAT']))
            # print float(vessel['LON'])
            #print mapping(coordinate)
            properties = {'LAT': vessel['LAT'],
                          'LON': vessel['LON'],
                          'SHIP_ID': vessel['SHIP_ID'],
                          'MMSI': vessel['MMSI'],
                          'IMO': vessel['IMO'],
                          'SPEED': vessel['SPEED'],
                          'HEADING': vessel['HEADING'],
                          'COURSE': vessel['COURSE'],
                          'STATUS': vessel['STATUS'],
                          'TIMESTAMP': vessel['TIMESTAMP'],
                          'DSRC': vessel['DSRC'],
                          'UTC_SECONDS': vessel['UTC_SECONDS'],
                          'NEW': str(vessel['NEW']),
                          'REQUEST_TIME': str(vessel['REQUEST_TIME'])}

            output.write({'geometry': mapping(coordinate), 'properties': properties})

        output.close()

    def export_vessels_to_web(self, nextgis_web_api_options, write_mode='rewrite'):
        """
        Export vessels NextGIS Web

        nextgis_web_api_options - dictionary, containing all information about NGW connection. Keys are:
        1. 'user' - NGW username (i.e. administrator)
        2. 'password' - NGW password
        3. 'url' - NGW url (i.e. http://ekazakov.nextgis.com/)
        4. 'resource_id' - id of resource, where vessels vector data are stored (i.e. 25)
        ! resource must have certain structure. You can initializate it with sample Shapefile or with
        self.init_NGW_resource_for_vessels function

        mode defines behaviour of exporter. Two ways are supported:
        1. rewrite - all existing in resource features will be deleted, then write new vessels
        2. append - append new vessels to existing features

        :param write_mode: 'rewrite' or 'append'.
        :param nextgis_web_api_options: All necessary API options as dict: {'url':'', 'username':'', 'password':'', 'resource_id': 0}
        """

        if write_mode == 'rewrite':
            self.__delete_all_features_from_NGW_resource(nextgis_web_api_options)
            for vessel in self.last_vessels_response:
                vessel_ngw = self.__describe_vessel_for_NGW(vessel)
                self.__add_feature_to_NGW_resource(vessel_ngw, nextgis_web_api_options)

        elif write_mode == 'append':
            for vessel in self.last_vessels_response:
                vessel_ngw = self.__describe_vessel_for_NGW(vessel)
                self.__add_feature_to_NGW_resource(vessel_ngw, nextgis_web_api_options)


    def automated_vessels_to_file (self, output_file, write_mode = 'new', output_type='GeoJSON', run_period=None, time_period=None, emulation=False):
        """
        Launching periodical requesting vessels and writing them to file

        output_type could be any type supported by Fiona lib:
        'ESRI Shapefile', 'MapInfo File', 'GeoJSON', 'PDS', 'FileGDB',
        'GPX', 'DXF', 'GMT', 'GPKG', 'BNA', 'GPSTrackMaker'

        run_period - time in minutes before function launches (i.e. 2)

        Three write_modes supported:
        1. new - will create new file with unique name everytime. To basename of output_file added timestamp
        2. rewrite - each time rewriting one file (output_file)
        3. append - append new vessels to existing features of output_file

        :param emulation: Emulate vessels instead of API requests
        :type emulation bool

        :param run_period: How often to run method
        :type run_period: int

        :param time_period: Time to observe vessels in minutes
        :type time_period: int

        :param write_mode: Mode of writing new data
        :type write_mode: str

        :param output_file: Output file(s) path
        :type output_file: str

        :param output_type: Output file(s) type
        :type output_type: str
        """

        start_time = time.time()
        while True:
            print 'Performing request...'
            self.get_vessels(time_period=time_period, emulation=emulation)

            if write_mode == 'new':
                now = datetime.utcnow().strftime('%Y%m%dT%H%M%S')

                new_name = os.path.join(os.path.dirname(output_file),
                                        '%s_%s.%s' % (os.path.basename(output_file).split('.')[0],
                                                      now,
                                                      os.path.basename(output_file).split('.')[1]))

                self.export_vessels_to_file(new_name, output_type=output_type, write_mode=write_mode)

            elif write_mode == 'append':
                self.export_vessels_to_file(output_file, output_type=output_type, write_mode=write_mode)
            elif write_mode == 'rewrite':
                self.export_vessels_to_file(output_file, output_type=output_type, write_mode=write_mode)
            else:
                print 'Unsupported mode'
                break

            time.sleep(run_period * 60.0 - ((time.time() - start_time) % (run_period * 60.0)))



    def automated_vessels_to_web(self, nextgis_web_api_options, run_period=None, time_period=None, write_mode='rewrite', emulation=False):
        """
        Launching periodical requesting vessels and writing them to NGW

        nextgis_web_api_options - dictionary, containing all information about NGW connection. Keys are:
        1. 'user' - NGW username (i.e. administrator)
        2. 'password' - NGW password
        3. 'url' - NGW url (i.e. http://ekazakov.nextgis.com/)
        4. 'resource_id' - id of resource, where vessels vector data are stored (i.e. 25)
        ! resource must have certain structure. You can initializate it with sample Shapefile or with
        self.init_NGW_resource_for_vessels function

        run_period - time in minutes before function launches (i.e. 2)

        Two write_modes supported:
        1. rewrite - each time rewriting all features in resource
        2. append - each time appending new vessels to resource

        :param write_mode: Mode of writing new data
        :type write_mode: str

        :param emulation: Emulate vessels instead of API requests
        :type emulation bool

        :param nextgis_web_api_options: All necessary API options
        :type nextgis_web_api_options: dict

        :param run_period:  How often to run method
        :type run_period: int

        :param time_period: Time to observe vessels in minutes
        :type time_period: int
        """

        start_time = time.time()
        while True:
            print 'Performing request...'
            self.get_vessels(time_period=time_period, emulation=emulation)

            self.export_vessels_to_web(nextgis_web_api_options, write_mode)

            time.sleep(run_period * 60.0 - ((time.time() - start_time) % (run_period * 60.0)))

    def init_NGW_resource_for_vessels(self, nextgis_web_api_options, display_name, keyname):
        """
        Initialization of new resource in NGW with scheme for vessels storing

        nextgis_web_api_options - dictionary, containing all information about NGW connection. Keys are:
        1. 'user' - NGW username (i.e. administrator)
        2. 'password' - NGW password
        3. 'url' - NGW url (i.e. http://ekazakov.nextgis.com/)
        4. 'resource_id' - id of PARENT resource, where vessels vector resource will be CREATED (i.e. 0)

        This method will create two new resources:
        1. Vector layer as a child of parent with given 'resource_id'
        2. Simple style as a child of new vector layer. You can change default style in MT_NGW_init_schemes.py

        :param nextgis_web_api_options: All necessary API options
        :type nextgis_web_api_options: dict

        :param display_name: display name for new vector layer
        :type display_name: str

        :param keyname: keyname for new vector layer
        :type keyname: str
        :return: answer of NGW API
        """
        scheme_init = MT_NGW_init_schemes(nextgis_web_api_options['resource_id'], display_name, keyname)
        resource = scheme_init.get_init_vector_layer()
        url = urljoin(nextgis_web_api_options['url'], 'api/resource/')
        r = requests.post(url, data=resource,
                          auth=(nextgis_web_api_options['user'], nextgis_web_api_options['password']))
        # print r.text
        r_loaded = json.loads(r.text)
        new_resource_id = r_loaded['id']

        style = scheme_init.get_init_mapserver_style(new_resource_id)
        r = requests.post(url, data=style,
                          auth=(nextgis_web_api_options['user'], nextgis_web_api_options['password']))
        # print r.text
        r_loaded = json.loads(r.text)

        return r_loaded


    #### Service private methods

    def __marine_traffic_vp_in_custom_area_request (self, timespan, MINLAT, MAXLAT, MINLON, MAXLON):
        #print '%s/%s/MINLAT:%s/MAXLAT:%s/MINLON:%s/MAXLON:%s/timespan:%s/protocol:jsono' % (self.MT_API_gate, self.MT_API_Key, MINLAT, MAXLAT, MINLON, MAXLON, timespan)
        r_loaded = []
        r = requests.get('%s/%s/MINLAT:%s/MAXLAT:%s/MINLON:%s/MAXLON:%s/timespan:%s/protocol:jsono' % (self.MT_API_gate, self.MT_API_Key, MINLAT, MAXLAT, MINLON, MAXLON, timespan))
        r_loaded = json.loads(r.text)
        #print r_loaded
        return r_loaded

    def __marine_traffic_vp_in_predifined_area_request(self, timespan):
        #print '%s/%s/timespan:%s/protocol:jsono' % (self.MT_API_gate, self.MT_API_Key, timespan)
        r_loaded = []
        r = requests.get('%s/%s/timespan:%s/protocol:jsono' % (self.MT_API_gate, self.MT_API_Key, timespan))
        #print r.text
        r_loaded = json.loads(r.text)
        #print r_loaded
        return r_loaded


    def __get_raw_vector_dataset_coordinates(self, fiona_dataset):
        dataset_coordinates = []
        for feature in fiona_dataset:
            current_geometry_type = feature['geometry']['type']
            if current_geometry_type != 'Polygon':
                continue
            dataset_coordinates.append(feature['geometry']['coordinates'][0])
        return dataset_coordinates

    def __get_reprojected_vector_dataset_coordinates (self, fiona_dataset, source_crs_epsg, dest_crs_epsg):
        source = Proj(init=source_crs_epsg)
        dest = Proj(init=dest_crs_epsg)
        new_dataset = []

        for feature in fiona_dataset:
            new_feature_geometry = []
            current_geometry_type = feature['geometry']['type']
            if current_geometry_type != 'Polygon':
                continue
            current_geometry_coordinates = feature['geometry']['coordinates'][0]
            for current_xy in current_geometry_coordinates:
                source_x = current_xy[0]
                source_y = current_xy[1]
                dest_x, dest_y = transform(source, dest,source_x,source_y)
                new_feature_geometry.append((dest_x,dest_y))
            new_dataset.append(new_feature_geometry)

        return new_dataset

    def __reproject_point (self, x, y, source_crs_epsg, dest_crs_epsg):
        source = Proj(init=source_crs_epsg)
        dest = Proj(init=dest_crs_epsg)
        dest_x, dest_y = transform(source, dest, x, y)
        return dest_x, dest_y

    def __get_bounds_from_coordinates(self, coordinates):
        x_coords = [item[0] for item in coordinates]
        y_coords = [item[1] for item in coordinates]
        return ({'x_min': min(x_coords), 'x_max': max(x_coords), 'y_min': min(y_coords), 'y_max': max(y_coords)})

    def __point_inside_polygon(self, point_x, point_y, polygon_coordinates):
        point = Point((point_x,point_y))
        polygon = shapely.geometry.Polygon(polygon_coordinates)
        return polygon.contains(point)

    def __add_feature_to_NGW_resource(self, feature, nextgis_web_api_options):
        url = urljoin(nextgis_web_api_options['url'],'api/resource/%s/feature/' % nextgis_web_api_options['resource_id'])
        r = requests.post(url, data=feature, auth=(nextgis_web_api_options['user'], nextgis_web_api_options['password']))
        #print r.text
        r_loaded = json.loads(r.text)
        return r_loaded

    def __delete_all_features_from_NGW_resource(self, nextgis_web_api_options):
        url = urljoin(nextgis_web_api_options['url'],'api/resource/%s/feature/' % nextgis_web_api_options['resource_id'])
        r = requests.delete(url, auth=(nextgis_web_api_options['user'], nextgis_web_api_options['password']))
        #print r.text
        r_loaded = json.loads(r.text)
        return r_loaded

    def __get_features_from_NGW_resource(self, nextgis_web_api_options):
        url = urljoin(nextgis_web_api_options['url'],'api/resource/%s/feature/' % nextgis_web_api_options['resource_id'])
        r = requests.get(url, auth=(nextgis_web_api_options['user'], nextgis_web_api_options['password']))
        #print r.text
        r_loaded = json.loads(r.text)
        return r_loaded

    def __describe_vessel_for_NGW(self, vessel_record, crs_id='epsg:3857'):
        x, y = self.__reproject_point(float(vessel_record['LON']), float(vessel_record['LAT']), 'epsg:4326', crs_id)
        geom = 'POINT (%s %s)' % (x, y)
        fields = vessel_record
        feature = {'extensions':{'attachment': None, 'description': None}, 'fields': fields, 'geom': geom}
        return json.dumps(feature)

    def __compare_features_are_equal(self, feature1, feature2):
        # Maybe some more deep comparison?
        if feature1 == feature2:
            return True
        else:
            return False