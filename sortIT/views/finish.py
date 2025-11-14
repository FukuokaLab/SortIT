from django.shortcuts import render


def finish(request):
    return render(request, "sortIT/thankyou.html")
