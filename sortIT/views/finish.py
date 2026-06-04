from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def finish(request):
    return render(request, "sortIT/thankyou.html")
