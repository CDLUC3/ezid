from django.shortcuts import render_to_response

def home(request):
  return render_to_response('home/home.html')

def community(request):
  return render_to_response('home/community.html')

def documentation(request):
  return render_to_response('home/documentation.html')

def outreach(request):
  return render_to_response('home/outreach.html')

def pricing(request):
  return render_to_response('home/pricing.html')

def understanding(request):
  return render_to_response('home/understanding.html')

def why(request):
  return render_to_response('home/why.html')