from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.conf import settings
import os
import fitz  # PyMuPDF
from PyPDF2 import PdfReader
from .models import Topic, Entry, Note, UploadedBook # Ensure all models are imported
from .forms import TopicForm, EntryForm
from django.utils.timezone import now  # ✅ Import now()


# Directory for storing uploaded PDFs
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'uploads')

# Home Page
def index(request):
    return render(request, 'new_learning_logs/index.html')

# Show Topics
@login_required
def topics(request):
    topics = Topic.objects.filter(owner=request.user).order_by('date_added')
    return render(request, 'new_learning_logs/topics.html', {'topics': topics})

# Show Single Topic
@login_required
def topic(request, topic_id):
    topic = Topic.objects.get(id=topic_id)
    if topic.owner != request.user:
        raise Http404
    entries = topic.entry_set.order_by('-date_added')
    return render(request, 'new_learning_logs/topic.html', {'topic': topic, 'entries': entries})

# Add New Topic
@login_required
def new_topic(request):
    if request.method == 'POST':
        form = TopicForm(data=request.POST)
        if form.is_valid():
            new_topic = form.save(commit=False)
            new_topic.owner = request.user
            new_topic.save()
            return redirect('new_learning_logs:topics')
    else:
        form = TopicForm()

    return render(request, 'new_learning_logs/new_topic.html', {'form': form})

# Add New Entry
@login_required        
def new_entry(request, topic_id):
    topic = Topic.objects.get(id=topic_id)

    if request.method == 'POST':
        form = EntryForm(data=request.POST)
        if form.is_valid():
            new_entry = form.save(commit=False)
            new_entry.topic = topic
            new_entry.save()
            return redirect('new_learning_logs:topic', topic_id=topic_id)
    else:
        form = EntryForm()

    return render(request, 'new_learning_logs/new_topic.html', {'topic': topic, 'form': form})

# Edit Entry
@login_required
def edit_entry(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    topic = entry.topic
    if topic.owner != request.user:
        raise Http404

    if request.method == 'POST':
        form = EntryForm(instance=entry, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('new_learning_logs:topic', topic_id=topic.id)
    else:
        form = EntryForm(instance=entry)

    return render(request, 'new_learning_logs/new_topic.html', {'entry': entry, 'topic': topic, 'form': form})

# Upload and Read PDF
@login_required
def read_pdf_view(request):
    pdf_url = None
    uploaded_books = UploadedBook.objects.filter(user=request.user)
    selected_book = None

    # Check session for last opened book
    selected_book_id = request.session.get("selected_book_id")
    if selected_book_id:
        selected_book = UploadedBook.objects.filter(id=selected_book_id, user=request.user).first()

    if request.method == "POST":
        if 'pdf_file' in request.FILES:
            pdf_file = request.FILES['pdf_file']
            title = pdf_file.name

            existing_book = UploadedBook.objects.filter(user=request.user, title=title).first()
            if existing_book:
                uploaded_book = existing_book
            else:
                uploaded_book = UploadedBook.objects.create(user=request.user, title=title, file=pdf_file)

            pdf_url = uploaded_book.file.url
            request.session["selected_pdf"] = pdf_url
            request.session["selected_book_id"] = uploaded_book.id
            return redirect("new_learning_logs:read_pdf")

        elif 'selected_book' in request.POST:
            selected_book = get_object_or_404(UploadedBook, id=request.POST['selected_book'], user=request.user)
            pdf_url = selected_book.file.url
            request.session['selected_pdf'] = pdf_url
            request.session['selected_book_id'] = selected_book.id
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse("Book selected", status=200)

        elif 'note_text' in request.POST:
            if selected_book:
                note, _ = Note.objects.get_or_create(user=request.user, book=selected_book)
                note.text = request.POST['note_text']
                note.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return HttpResponse("Notes saved successfully", status=200)
            elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse("No book selected", status=400)

    pdf_url = request.session.get('selected_pdf', None)
    absolute_pdf_url = request.build_absolute_uri(pdf_url) if pdf_url else None

    print(f"Final PDF URL sent to template: {absolute_pdf_url}")

    note = None
    if selected_book:
        note = Note.objects.filter(user=request.user, book=selected_book).first()

    response = render(request, "new_learning_logs/read_pdf.html", {
        "pdf_url": absolute_pdf_url,
        "note": note,
        "uploaded_books": uploaded_books,
        "selected_book": selected_book,
        "timestamp": now().timestamp(),
    })
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response

# Extract PDF Text (unchanged)
def extract_pdf_content(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    pdf_text = ""
    for page in pdf_reader.pages:
        pdf_text += page.extract_text() + "\n"
    return pdf_text