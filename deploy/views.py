from django.http import HttpResponse
from deploy.forms import Migrate


def site_migrate(request, d):
    
    f = Migrate()
    x = " %s " %( f,) 
    return HttpResponse( x)


def home(request):

    return HttpResponse('home')    
