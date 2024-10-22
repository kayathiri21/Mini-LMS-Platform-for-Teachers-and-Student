from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
     path('', views.landing_page, name='landing'),
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='lms_app/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('accounts/signup/student/', views.student_signup, name='student_signup'),
    path('accounts/signup/teacher/', views.teacher_signup, name='teacher_signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('course/create/', views.create_course, name='create_course'),
     path('course/<int:course_id>/', views.course_detail, name='course_detail'), 
    path('course/<int:course_id>/quiz/create/', views.create_quiz, name='create_quiz'),
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('quiz/delete/<int:quiz_id>/',views.delete_quiz, name='delete_quiz'),
]