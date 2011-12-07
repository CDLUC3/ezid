from django.shortcuts import render_to_response

d = {'1_menu': 'manage'}

def index(request):
  return render_to_response('home/home.html', d)

def details(request):
  pass

def understanding(request):
  pass
