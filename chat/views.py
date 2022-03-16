from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from chat.models import Message
from chat.forms import SignUpForm
from chat.serializers import MessageSerializer
from .models import Profile
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect
from ChatApp import settings

def index(request):
    """
        Django Project Starts From here!
        if it's login it can directly go to the chat page otherwise login page on get request...
        if it's not login it can directly go to the Login/Register page...
    """
    if request.user.is_authenticated:

        return redirect('chats')
    if request.method == 'GET':
        return render(request, 'chat/index.html', {})
    if request.method == "POST":
        username, password = request.POST['username'], request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)

        else:
            return render(request, 'chat/index.html',
                          {'errors': "Wrong Login Id/Password OR User DoesNot Exist!"}
                          )
    return redirect('chats')



@csrf_exempt
def message_list(request, sender=None, receiver=None):
    """
            List all required messages, or start a new chat.
    """
    if request.method == 'GET':
        messages = Message.objects.filter(sender_id=sender, receiver_id=receiver, is_read=False)
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        for message in messages:
            message.is_read = True
            message.save()
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


def register_view(request):
    """
        Render registration Page
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user.set_password(password)
            user.email = username
            user.save()

            import random
            code = str(random.random())
            profile = Profile(user=user, email_code=code)
            profile.save()

            if code:
                print()
                subject = "Verification Email"
                body = {
                    'subject': "Verification | DBS Chat System",
                    'message': 'verification code is: ' + str(code),
                }
                message = '\n'.join(body.values())
                sender = settings.EMAIL_HOST_USER
                recipient = [username, ]
                try:
                    send_mail(subject, message, sender, recipient)
                    print("+++++++ Email Sent +++++++")
                except Exception as e:
                    return HttpResponse(str(e))

            else:
                return HttpResponse('Make sure all fields are entered and valid.')

            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('chats')
        else:
            print(form.errors)
            template = 'chat/register.html'
            context = {'form': form,
                       'errors': form.errors
                       }
            return render(request, template, context)

    else:
        form = SignUpForm()
    template = 'chat/register.html'
    context = {'form': form}
    return render(request, template, context)


def chat_view(request):
    """
        Main Page of Chat App where all the users come at left side.
        and chat at the right side
    """
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == "GET":
        profile = Profile.objects.get(user=User.objects.get(email=request.user.email))
        return render(request, 'chat/chat.html',
                      {'users': User.objects.exclude(username=request.user.username),
                       'verified': profile.is_verified})


def message_view(request, sender, receiver):
    """
        If user is not authenticated then it will go to the index route
        otherwise will go to the chat dashboard page
    """
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == "GET":
        profile = Profile.objects.get(user=User.objects.get(email=request.user.email))
        return render(request, "chat/messages.html",
                      {'users': User.objects.exclude(username=request.user.username),
                       'receiver': User.objects.get(id=receiver),
                       'messages': Message.objects.filter(sender_id=sender, receiver_id=receiver) |
                                   Message.objects.filter(sender_id=receiver, receiver_id=sender),
                       'verified': profile.is_verified})


def send_email(request):
    import random
    profile = Profile.objects.get(user=User.objects.get(email=request.user.email))
    code = str(random.random())
    if code:
        print()
        subject = "Verification Email"
        body = {
            'subject': "Verification | DBS Chat System",
            'message': 'verification code is: ' + str(code),
        }
        message = '\n'.join(body.values())
        sender = settings.EMAIL_HOST_USER
        recipient = [profile.user.username, ]
        try:
            send_mail(subject, message, sender, recipient)
            print("+++++++ Email Sent +++++++")
            return HttpResponse('Email Sent')
        except Exception as e:
            return HttpResponse(str(e))

    else:
        return HttpResponse('Make sure all fields are entered and valid.')


def verify(request):
    code = request.POST.get('code', None)
    if code:
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.email_code == code:
                profile.is_verified = True
                profile.save()
                return redirect('chats')
            else:
                return HttpResponse('Wrong Verification Code!')
        except Exception as e:
            return HttpResponse(str(e))
    else:
        return HttpResponse('No Verification Code Found')
    return redirect('chats')
