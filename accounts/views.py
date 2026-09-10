from django.shortcuts import render
from django.contrib.auth import views as auth_views
from django.utils.decorators import method_decorator

try:
    from django_ratelimit.decorators import ratelimit
except ImportError:
    def ratelimit(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator


@method_decorator(ratelimit(key='ip', rate='15/m', method='POST', block=False), name='dispatch')
class RateLimitedLoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST' and getattr(request, 'limited', False):
            form = self.get_form()
            form.add_error(None, "Troppi tentativi di accesso. Per motivi di sicurezza attendi qualche istante prima di riprovare.")
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().dispatch(request, *args, **kwargs)


def placeholder(request):
    return render(request, 'accounts/login.html')


def logout_view(request):
    """
    Log out the user, flush the session, and redirect to the login page.
    Supports both GET (e.g. from top navigation dropdown links) and POST
    to prevent HTTP 405 Method Not Allowed errors.
    """
    from django.contrib.auth import logout
    from django.shortcuts import redirect
    logout(request)
    return redirect('login')
