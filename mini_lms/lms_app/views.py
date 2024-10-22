from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import *
from django.db.models import Count, Avg
from django.db import transaction

import html
# views.py

import requests
from django.contrib.auth import login, authenticate,logout
from django.urls import reverse
from .forms import StudentSignUpForm, TeacherSignUpForm,CourseForm, QuizForm

def is_teacher(user):
    return user.groups.filter(name='Teacher').exists()
def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'lms_app/landing.html')

def student_signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = StudentSignUpForm()
    return render(request, 'lms_app/auth/student_signup.html', {'form': form})

def teacher_signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TeacherSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Teacher account created successfully!')
            return redirect('dashboard')
    else:
        form = TeacherSignUpForm()
    return render(request, 'lms_app/auth/teacher_signup.html', {'form': form})

# @login_required
# def dashboard(request):
#     if request.user.groups.filter(name='Teacher').exists():
#         # Teacher Dashboard
#         courses = Course.objects.filter(teacher=request.user)
#         context = {
#             'courses': courses,
#             'total_courses': courses.count(),
#             'total_quizzes': Quiz.objects.filter(course__teacher=request.user).count(),
#             'recent_quizzes': QuizSubmission.objects.filter(
#                 quiz__course__teacher=request.user
#             ).order_by('-submitted_at')[:5]
#         }
#         return render(request, 'lms_app/teacher/dashboard.html', context)
#     else:
#         # Student Dashboard
#         enrollments = StudentEnrollment.objects.filter(student=request.user)
#         context = {
#             'enrollments': enrollments,
#             'total_courses': enrollments.count(),
#             'completed_quizzes': QuizSubmission.objects.filter(student=request.user).count(),
#             'recent_submissions': QuizSubmission.objects.filter(
#                 student=request.user
#             ).order_by('-submitted_at')[:5]
#         }
#         return render(request, 'lms_app/student/dashboard.html', context)
 
@login_required
def dashboard(request):
    if request.user.groups.filter(name='Teacher').exists():
        # Get course and quiz counts
        total_courses = Course.objects.filter(teacher=request.user).count()
        total_quizzes = Quiz.objects.filter(course__teacher=request.user).count()
    
    # Get total enrolled students (distinct)
        total_students = StudentEnrollment.objects.filter(
        course__teacher=request.user
    ).values('student').distinct().count()
    
    # Get courses with enrollment counts
        courses = Course.objects.filter(teacher=request.user).annotate(
        student_count=Count('studentenrollment'),
        quiz_count=Count('quizzes')
    ).order_by('-created_at')
    
    # Get recent quiz submissions
        recent_quizzes = QuizSubmission.objects.filter(
        quiz__course__teacher=request.user
    ).select_related('student', 'quiz').order_by('-submitted_at')[:5]
    
    # Get quiz results overview
        quiz_results = QuizSubmission.objects.filter(
        quiz__course__teacher=request.user
    ).values('quiz__title').annotate(
        avg_score=Avg('score'),
        student_count=Count('student', distinct=True)
    )
        # Handle adding feedback
        if request.method == 'POST':
            submission_id = request.POST.get('submission_id')
            feedback_content = request.POST.get('feedback')

            if submission_id and feedback_content:
                submission = get_object_or_404(QuizSubmission, id=submission_id)
                feedback, created = Feedback.objects.get_or_create(submission=submission, teacher=request.user)
                feedback.content = feedback_content
                feedback.save()
                messages.success(request, 'Feedback added successfully!')
    
        context = {
        'total_courses': total_courses,
        'total_quizzes': total_quizzes,
        'total_students': total_students,
        'courses': courses,
        'recent_quizzes': recent_quizzes,
        'quiz_results': quiz_results,
    }
        return render(request, 'lms_app/teacher/dashboard.html', context)
    else:
       # Student Dashboard
        enrollments = StudentEnrollment.objects.filter(student=request.user)
        completed_quizzes = QuizSubmission.objects.filter(student=request.user).count()
        recent_submissions = QuizSubmission.objects.filter(
            student=request.user
        ).order_by('-submitted_at')[:5]

        # Get quizzes available to take
        available_quizzes = []
        for enrollment in enrollments:
            available_quizzes.extend(Quiz.objects.filter(course=enrollment.course))

        # Get quiz results overview for the student
        quiz_results = QuizSubmission.objects.filter(
            student=request.user
        ).values('quiz__title').annotate(
            avg_score=Avg('score'),
            student_count=Count('student', distinct=True)
        )
        # Get feedback for completed quizzes
        feedbacks = Feedback.objects.filter(submission__student=request.user)


        context = {
            'enrollments': enrollments,
            'total_courses': enrollments.count(),
            'completed_quizzes': completed_quizzes,
            'recent_submissions': recent_submissions,
            'available_quizzes': available_quizzes,  # Add available quizzes to context
            'quiz_results': quiz_results, 
              'feedbacks': feedbacks, # Add quiz results to context
        }
        return render(request, 'lms_app/student/dashboard.html', context)

@login_required
@user_passes_test(is_teacher)
def create_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.save()
            messages.success(request, 'Course created successfully!')
            return redirect('dashboard')
    else:
        form = CourseForm()
    return render(request, 'lms_app/teacher/create_course.html', {'form': form})

@login_required
@user_passes_test(is_teacher)
def create_quiz(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            try:
                # Create quiz in a transaction to ensure all related data is saved
                with transaction.atomic():
                    quiz = form.save(commit=False)
                    quiz.course = course
                    quiz.save()
                    
                    # Fetch and create questions if fetch_external is checked
                    if form.cleaned_data.get('fetch_external'):
                        quiz_title = form.cleaned_data.get('title', '').lower()
                        print(f"Fetching questions for quiz: {quiz_title}")  # Debugging

                        # Using OpenTDB API as the primary source for reliability
                        api_url = 'https://opentdb.com/api.php?amount=5&type=multiple'
                        
                        # Add category based on quiz title
                        if any(keyword in quiz_title for keyword in ['python', 'java', 'javascript', 'programming']):
                            api_url += '&category=18'  # Computer Science
                        
                        print(f"Fetching from API: {api_url}")  # Debugging
                        response = requests.get(api_url)
                        
                        if response.status_code != 200:
                            raise Exception(f"API returned status code: {response.status_code}")
                        
                        data = response.json()
                        if data.get('response_code') != 0:  # OpenTDB specific check
                            raise Exception("API returned an error response")
                            
                        questions_data = data.get('results', [])
                        
                        if not questions_data:
                            raise Exception("No questions received from API")
                            
                        print(f"Received {len(questions_data)} questions")  # Debugging
                        
                        # Create questions and choices
                        for item in questions_data:
                            # Create question
                            question = Question.objects.create(
                                quiz=quiz,
                                text=html.unescape(item['question']),  # Decode HTML entities
                                is_external=True
                            )
                            print(f"Created question ID {question.id}: {question.text}")  # Debugging
                            
                            # Create correct choice
                            correct_choice = Choice.objects.create(
                                question=question,
                                text=html.unescape(item['correct_answer']),
                                is_correct=True
                            )
                            print(f"Created correct choice ID {correct_choice.id}: {correct_choice.text}")  # Debugging
                            
                            # Create incorrect choices
                            for incorrect_answer in item['incorrect_answers']:
                                incorrect_choice = Choice.objects.create(
                                    question=question,
                                    text=html.unescape(incorrect_answer),
                                    is_correct=False
                                )
                                print(f"Created incorrect choice ID {incorrect_choice.id}: {incorrect_choice.text}")  # Debugging
                        
                        # Verify questions were created
                        question_count = quiz.questions.count()
                        print(f"Total questions created for quiz: {question_count}")  # Debugging
                        
                        if question_count == 0:
                            raise Exception("Failed to create any questions")
                            
                messages.success(request, f'Quiz created successfully with {question_count} questions!')
                return redirect('course_detail', course_id=course.id)
                
            except Exception as e:
                print(f"Error creating quiz: {str(e)}")  # Debugging
                messages.error(request, f'Error creating quiz: {str(e)}')
                return render(request, 'lms_app/teacher/create_quiz.html', {'form': form, 'course': course})
    else:
        form = QuizForm()
    
    return render(request, 'lms_app/teacher/create_quiz.html', {'form': form, 'course': course})
@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if student is enrolled in the course
    if not StudentEnrollment.objects.filter(student=request.user, course=quiz.course).exists():
        messages.error(request, 'You must be enrolled in the course to take this quiz')
        return redirect('dashboard')

    quiz.questions_list = quiz.questions.prefetch_related('choices').all()

    if request.method == 'POST':
        score = 0
        total_questions = quiz.questions.count()

        if total_questions == 0:
            messages.error(request, 'This quiz has no questions.')
            return redirect('dashboard')

        unanswered_questions = [question.id for question in quiz.questions.all() 
                              if not request.POST.get(f'question_{question.id}')]

        if unanswered_questions:
            messages.error(request, 'Please answer all questions before submitting.')
            return render(request, 'lms_app/student/take_quiz.html', {
                'quiz': quiz,
                'has_questions': True,
                'unanswered_questions': unanswered_questions
            })

        try:
            with transaction.atomic():
                # Create the submission
                submission = QuizSubmission.objects.create(
                    student=request.user,
                    quiz=quiz
                )

                # Process each answer
                for question in quiz.questions.all():
                    selected_choice_id = request.POST.get(f'question_{question.id}')
                    selected_choice = get_object_or_404(Choice, id=selected_choice_id)

                    if selected_choice.is_correct:
                        score += 1

                    StudentAnswer.objects.create(
                        submission=submission,
                        question=question,
                        selected_choice=selected_choice
                    )

                # Calculate and save the final score
                submission.score = (score / total_questions) * 100
                submission.save()

                messages.success(
                    request, 
                    f'Quiz submitted successfully! Your score: {submission.score:.2f}%'
                )
                # Redirect to dashboard without submission_id parameter
                return redirect('dashboard')

        except Exception as e:
            messages.error(request, f'An error occurred while submitting your quiz: {str(e)}')
            print(f"Quiz submission error: {str(e)}")  # For debugging
            return redirect('take_quiz', quiz_id=quiz_id)

    context = {
        'quiz': quiz,
        'has_questions': quiz.questions.exists(),
    }
    return render(request, 'lms_app/student/take_quiz.html', context)
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing')  
@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.user.groups.filter(name='Teacher').exists():
        quizzes = Quiz.objects.filter(course=course)
        return render(request, 'lms_app/teacher/course_detail.html', {'course': course, 'quizzes': quizzes})
    
    elif StudentEnrollment.objects.filter(student=request.user, course=course).exists():
        quizzes = Quiz.objects.filter(course=course)
        return render(request, 'lms_app/student/course_detail.html', {'course': course, 'quizzes': quizzes})
    
    else:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('dashboard')

@login_required
@user_passes_test(is_teacher)
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__teacher=request.user)
    
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, 'Quiz deleted successfully!')
        return redirect('course_detail', course_id=quiz.course.id)
    
    # Redirect if not a POST request
    return redirect('course_detail', course_id=quiz.course.id)