from django.shortcuts import render

def placeholder(request):
    return render(request, 'accounts/login.html')
