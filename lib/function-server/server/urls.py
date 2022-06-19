"""server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from datetime import datetime
from functools import wraps
import json
from timeit import timeit
from django.contrib import admin
from django.urls import path
from django.template.loader import render_to_string
from django.shortcuts import render
from django.http import HttpResponse
import pdfkit
import pandas as pd


def validate_zoning_data(function):
    udc_df = pd.read_csv(
        '/mnt/f/Windows/Downloads/feasibility data UDC POC.csv'
    )
    df = pd.read_csv(
        '/mnt/f/Windows/Downloads/feasibility data FULL ASSESSOR DATA POC.csv'
    )
    df = df.fillna('')
    udc_df = udc_df.fillna('')
    print(df)
    print(df['LANDMEAS'].describe())

    @wraps(function)
    def wrap(request, *args, **kwargs):
        context = df[df['ADDRESS_OL'] ==
                     request.GET['address']].to_dict(orient='records')
        adu_area = int(request.GET['adu_area'])
        additional_built_areas = int(request.GET['additional_built_areas'])
        adu_height = int(request.GET['adu_height'])
        if len(context) > 0:
            context = context[0]
            if context['LANDMEAS'] <= 1:
                context['LANDMEAS'] = context['GISAREA']
            context['adu_area'] = adu_area
            context['adu_height'] = adu_height
            context['additional_built_areas'] = additional_built_areas
            if context['LANDMEAS'] < 6500 and adu_area > 650:
                return HttpResponse('Size not allowed, too large for lot zoning.')
            elif context['LANDMEAS'] >= 6500 and adu_area > .1 * context['LANDMEAS']:
                return HttpResponse('Size not allowed, too large for lot zoning.')
            context['total_new_liveable_area'] = adu_area + context['SQFT']
            context['total_proposed_lot_coverage_area'] = adu_area + \
                context['POOLAREA'] + context['SQFT'] + additional_built_areas
            matching_zoning = udc_df[udc_df['CURZONE_OL'] ==
                                     context['ZONING']].to_dict(orient='records')
            print(matching_zoning)
            if len(matching_zoning) == 0:
                return HttpResponse('Zoning not found.')
            matching_zoning = matching_zoning[0]
            lot_coverage = matching_zoning['lot coverage']
            context['lot_coverage_maximum'] = int(lot_coverage[:-1])/100
            context['lot_coverage'] = context['total_proposed_lot_coverage_area'] / \
                context['LANDMEAS']
            if context['lot_coverage'] > context['lot_coverage_maximum']:
                return HttpResponse('Lot coverage too high.')
            context['height'] = matching_zoning['Height']
            if adu_height > int(context['height'][:-1]):
                return HttpResponse('ADU height too high.')
            context['perimeter_yard'] = matching_zoning['Perimeter yard']

            context['lot_coverage_maximum'] = context['lot_coverage_maximum'] * 100
            context['lot_coverage'] = context['lot_coverage'] * 100
            context['last_name'] = context['A'].split(' ')[0]
            context['today'] = datetime.now()
            return function(request, context, *args, **kwargs)
        return HttpResponse('No data found')

    return wrap


@validate_zoning_data
def pdf_view(request, context):
    options = {
        'page-size': 'A3',
        'orientation': 'Landscape',
        'margin-top': '0.25in',
        'margin-right': '0.25in',
        'margin-bottom': '0.25in',
        'margin-left': '0.25in',
    }
    # allow additional built areas.
    doc = render_to_string('adu.html', context)
    pdf = pdfkit.from_string(doc, False, options)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=adu.pdf'
    return response


@validate_zoning_data
def html_view(request, context):
    return render(request, 'adu.html', context)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('pdf/', pdf_view),
    path('html/', html_view),
]
