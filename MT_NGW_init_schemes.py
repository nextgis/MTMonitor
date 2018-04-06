import json

class MT_NGW_init_schemes():

    vector_layer_resoure = ''
    mapserver_style_resource = ''

    def __init__(self, parent_id, display_name, keyname):
        self.parent_id = parent_id
        self.display_name = display_name
        self.keyname = keyname


    def get_init_mapserver_style(self, new_resource_id):
        default_mapserver_xml = '''
                <map>
                  <symbol>
                    <type>ellipse</type>
                    <name>circle</name>
                    <points>1 1</points>
                    <filled>true</filled>
                  </symbol>
                  <layer>
                    <class>
                      <style>
                        <color blue="98" green="180" red="253"/>
                        <outlinecolor blue="64" green="64" red="64"/>
                        <symbol>circle</symbol>
                        <size>6</size>
                      </style>
                    </class>
                  </layer>
                  <legend>
                    <keysize y="15" x="15"/>
                    <label>
                      <size>12</size>
                      <type>truetype</type>
                      <font>regular</font>
                    </label>
                  </legend>
                </map>
                '''

        style = {"mapserver_style" : {
            "xml" : default_mapserver_xml
        },
            "resource": {
                "cls": "mapserver_style",
                "description": None,
                "display_name": self.display_name,
                "keyname": '%s style' % self.keyname,
                "parent": {
                    'id':new_resource_id}
            }
        }
        return json.dumps(style)

    def get_init_vector_layer (self):
        resource = {
            'resource':
                {'cls': 'vector_layer',
                 'parent': {
                     'id': self.parent_id
                 },
                 'display_name': self.display_name,
                 'keyname': self.keyname,
                 'description': 'Vessels from MarineTraffic.com'
                 },
            'resmeta':
                {'items':
                     {}
                 },
            'vector_layer': {
                'srs': {'id': 3857},
                'geometry_type': 'POINT',
                'fields': [
                    {
                        'keyname': 'LAT',
                        'datatype': "STRING"
                    },
                    {
                        "keyname": "LON",
                        "datatype": "STRING"
                    },
                    {
                        "keyname": "MMSI",
                        "datatype": "STRING"
                    },
                    {
                        "keyname": "IMO",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "SPEED",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "HEADING",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "COURSE",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "STATUS",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "TIMESTAMP",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "DSRC",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "UTC_SECONDS",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "NEW",
                        "datatype": "STRING",
                    },
                    {
                        "keyname": "REQUEST_TIME",
                        "datatype": "STRING",
                    }
                ]
            }
        }

        return json.dumps(resource)






