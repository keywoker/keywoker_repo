# -*- encoding: utf-8 -*-

import base64
import urllib
import cStringIO
from cStringIO import StringIO
import zlib
import os
import tempfile
import csv
from openerp.osv import fields, osv
import logging
import PIL
from PIL import Image
from flask import make_response

logger = logging.getLogger(__name__)

class csv_parser(osv.osv_memory):
    _name = 'product.csv.image'
    _description = 'Making CSV for Product Image Import'
    _columns = {
        'file_data': fields.binary('Source File', required=True),
        'file_fname': fields.char('Source File Name', size=128, required=True),
    }

    _defaults = {
        'file_fname': lambda *a: '',
    }

    def get_csv(self, cr, uid, ids, context=None):
        height = 500
        data = self.browse(cr, uid, ids)[0]
        file = data.file_data
        filename = data.file_fname
        recordlist = base64.decodestring(file).split('\n')
        h_raw = recordlist[0]
        out = False
        lines = recordlist[1:]
        elem = []
        for line in lines:
            elem.append(line.split(','))
        headers = h_raw.split(',')
        length = len(headers)
        headers[length-1] = headers[length-1].rstrip()
        id_index = 0
        image_index = False
        for index, value in enumerate(headers):
            if value == 'id':
                id_index = index
            if value == 'image':
                image_index = index

        out = csv.writer(open("/projects/new_images.csv", "w"), delimiter=',')
        res_headers = [headers[id_index], headers[image_index]]
        out.writerow(res_headers)
        count = 1
        for e in elem:
            if e[id_index]:
                logger.error('Product %s ID %s', count, e[id_index])
                if e[image_index]:
                    if len(e[image_index]) > 9:
                        if e[image_index][-3:] == 'jpg':
                            try:
                                # response = urllib.urlopen(e[image_index])
                                # e[image_index] = base64.b64encode(response.read())
                                file = cStringIO.StringIO(urllib.urlopen(e[image_index]).read())  # FOR IMAGE RESIZE
                                img = Image.open(file)
                                heightPercent = (height / float(img.size[1]))
                                width = int((float(img.size[0]) * float(heightPercent)))
                                # widthPercent = (width / float(img.size[0]))
                                # height = int((float(img.size[1]) * float(widthPercent)))
                                res_image = img.resize((width, height), Image.ANTIALIAS)
                                output = StringIO()
                                res_image.save(output, format='JPEG')
                                im_data = output.getvalue()
                                e[image_index] = base64.b64encode(im_data)
                                res_line = [e[id_index], e[image_index]]
                                out.writerow(res_line)
                            except IOError:
                                continue
                count += 1
        return out

    # def get_csv(self, cr, uid, ids, context=None):
    #     data = self.browse(cr, uid, ids)[0]
    #     file = data.file_data
    #     filename = data.file_fname
    #     recordlist = base64.decodestring(file).split('\n')
    #     h_raw = recordlist[0]
    #     out = False
    #     lines = recordlist[1:]
    #     elem = []
    #     for line in lines:
    #         elem.append(line.split(','))
    #     headers = h_raw.split(',')
    #     length = len(headers)
    #     headers[length-1] = headers[length-1].rstrip()
    #     id_index = 0
    #     image_index = False
    #     for index, value in enumerate(headers):
    #         if value == 'id':
    #             id_index = index
    #         if value == 'image':
    #             image_index = index
    #
    #     out = csv.writer(open("/projects/new_images.csv", "w"), delimiter=',')
    #     res_headers = [headers[id_index], headers[image_index]]
    #     out.writerow(res_headers)
    #     for e in elem:
    #         if e[id_index]:
    #             if e[image_index]:
    #                 if len(e[image_index]) > 9:
    #                     if e[image_index][-3:] == 'jpg':
    #                         try:
    #                             response = urllib.urlopen(e[1])
    #                             e[image_index] = base64.b64encode(response.read())
    #                             res_line = [e[id_index], e[image_index]]
    #                             out.writerow(res_line)
    #                         except IOError:
    #                             continue
    #     return out3