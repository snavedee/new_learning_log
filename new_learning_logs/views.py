from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404
from .models import Topic, Entry
from .forms import TopicForm, EntryForm
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import os


# Define a directory for storing uploaded files
UPLOAD_DIR = 'uploaded_pdfs'
# Create your views here.
def index(request):
    '''The home page for New Learning Log.'''
    return render(request, 'new_learning_logs/index.html')

@login_required
def topics(request):
    '''Show all topics.'''
    topics = Topic.objects.filter(owner=request.user).order_by('date_added')
    context = {'topics': topics}
    return render(request, 'new_learning_logs/topics.html', context)

@login_required
def topic(request, topic_id):
    '''Show a single topic and all it's entries.'''
    topic = Topic.objects.get(id=topic_id)
    # Make sure the topic belongs to the current user.
    if topic.owner != request.user:
        raise Http404
    entries = topic.entry_set.order_by('-date_added')
    context = {'topic': topic, 'entries': entries}
    return render(request, 'new_learning_logs/topic.html', context)

def new_topic(request):
    '''Add a new topic.'''
    if request.method != 'POST':
        # No data submitted; create a blank form.
        form = TopicForm()
    else:
        # POST data submitted; process data.
        form = TopicForm(data=request.POST)
        if form.is_valid():
            new_topic = form.save(commit=False)
            new_topic.owner = request.user
            new_topic.save()
            return redirect('new_learning_logs:topics')
    # Ensure that the form is always rendered, even if it's invalid.
    context = {'form': form} # Prepare context for rendering
    return render(request, 'new_learning_logs/new_topic.html', context)

@login_required        
def new_entry(request, topic_id):
    '''Add a new entry for a particular topic.'''
    topic = Topic.objects.get(id=topic_id)

    if request.method != 'POST':
        # No data submitted; create a blank form.
        form = EntryForm()
    else:
        # Post data submitted; process data.
        form = EntryForm(data=request.POST)
        if form.is_valid():
            new_entry = form.save(commit=False)
            new_entry.topic = topic
            new_entry.save()
            return redirect('new_learning_logs:topic', topic_id=topic_id)
    # Display a blank or invalid form.
    context = {'entry': None, 'topic': topic, 'form': form}  # Prepare context for rendering
    return render(request, 'new_learning_logs/new_topic.html', context)  # Ensure this line is always reached
        
@login_required
def edit_entry(request, entry_id):
    '''Edit an existing entry.'''
    entry = Entry.objects.get(id=entry_id)
    topic = entry.topic
    if topic.owner != request.user:
        raise Http404

    if request.method != 'POST':
        # Initial request; prefill form with the current entry.
        form = EntryForm(instance=entry)
    else:
        # POST data submitted; process data.
        form = EntryForm(instance=entry, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('new_learning_logs:topic', topic_id=topic.id)

        
    # Display a blank or invalid form.
    context = {'entry': None, 'topic': topic,'form': form}
    return render(request, 'new_learning_logs/new_topic.html', context)

@login_required
def read_pdf_view(request):
    pdf_content = []
    num_pages = 0
    page_number = request.GET.get('page', 1)

    if request.method == 'POST' and 'pdf_file' in request.FILES:
        pdf_file = request.FILES["pdf_file"]
        fs = FileSystemStorage(location=UPLOAD_DIR)
        saved_file = fs.save(pdf_file.name, pdf_file)
        request.session['saved_pdf_path'] = os.path.join(UPLOAD_DIR, pdf_file.name)

    # Retrieve the saved PDF file path
    pdf_path = request.session.get('saved_pdf_path', None)
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            num_pages = len(pdf_reader.pages)
            pdf_content = [page.extract_text() or "No content on this page" for page in pdf_reader.pages]

    # Paginate the extracted content
    paginator = Paginator(pdf_content, 1)  # Show one page at a time
    page_obj = paginator.get_page(page_number)

        
        
    context = {
        'page_obj': page_obj,
        'num_pages': num_pages,
    }
    return render(request, 'new_learning_logs/read_pdf.html', context)

def extract_pdf_content(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    pdf_text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        pdf_text += page.extract_text() + "\n"
    return pdf_text