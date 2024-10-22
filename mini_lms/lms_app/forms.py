from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import *
class StudentSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            # Add user to Student group
            student_group = Group.objects.get(name='Student')
            user.groups.add(student_group)
        return user

class TeacherSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    teacher_code = forms.CharField(max_length=50, required=True, 
                                 help_text="Enter the teacher registration code")
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "teacher_code")
    
    def clean_teacher_code(self):
        code = self.cleaned_data.get('teacher_code')
        if code != "TEACHER2024":  # In production, use environment variables for this
            raise forms.ValidationError("Invalid teacher code")
        return code
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            # Add user to Teacher group
            teacher_group = Group.objects.get(name='Teacher')
            user.groups.add(teacher_group)
        return user
class CourseForm(forms.ModelForm):
    class Meta:
        model =Course
        fields = ['title', 'description', 'duration']  # Include any other fields your Course model has

class QuizForm(forms.ModelForm):
    fetch_external = forms.BooleanField( required=False,
        initial=True,
        label='Fetch questions from external source',
        help_text='Check this to automatically generate questions')

    class Meta:
        model = Quiz
        fields = ['title', 'course', 'duration', 'fetch_external']  # Include any other fields your Quiz model has

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['title'].widget.attrs.update({'class': 'form-control'})
        self.fields['duration'].widget.attrs.update({'class': 'form-control'})
        self.fields['course'].widget.attrs.update({'class': 'form-control'})  # Assuming 'course' is a ForeignKey field
        self.fields['fetch_external'].widget.attrs.update({'class': 'form-check-input'})
