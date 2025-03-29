from django.db import models
from django.contrib.auth.models import User

class Topic(models.Model):
    '''A topic the user is learning about.'''
    text = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

class Entry(models.Model):
    '''Something specific learned about a topic.'''
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    text = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'entries'

    def __str__(self):
        '''Return a string representation of the model.'''
        return self.text

# ✅ Move UploadedBook ABOVE Note
class UploadedBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploaded_pdfs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Changed to ForeignKey
    book = models.ForeignKey(UploadedBook, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField(blank=True)

    def __str__(self):
        return f"Note by {self.user.username} for {self.book.title if self.book else 'no book'}"
