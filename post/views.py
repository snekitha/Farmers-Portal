from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.files.base import ContentFile

from django.db import connection, transaction

import datetime
import os

# Create your views here.
from .models import POST_CATEGORIES
from User.models import check_if_auth_user
from Farmers_Portal.settings import MEDIA_ROOT

from collections import namedtuple

def namedtuplefetchall(cursor):
	"Return all rows from a cursor as a namedtuple"
	desc = cursor.description
	nt_result = namedtuple('Result', [col[0] for col in desc])
	return [nt_result(*row) for row in cursor.fetchall()]

#CRUD implemented here
def posts_create(request):
	check = check_if_auth_user(request)
	current_user = None
	if check:
		cursor = connection.cursor()
		if request.session["user_class"] == 'E':
			query = "SELECT * FROM User_expert WHERE `User_expert`.'user_id' = %s"
		else:
			query = "SELECT * FROM User_farmer WHERE `User_farmer`.'user_id' = %s"

		cursor.execute(query, [check, ])
		result = namedtuplefetchall(cursor)
		current_user = result[0]

	if current_user is None:
		messages.error(request, "Perform Login first")
		return redirect("home:welcome")

	if request.method == "POST":
		title = request.POST.get('post_title')
		disc = request.POST.get('post_disc')
		category = request.POST.get('post_category')
		try:
			image = request.FILES['post_image']
		except Exception:
			image = None

		cursor = connection.cursor()

		if image:
			full_filename = os.path.join(MEDIA_ROOT, image.name)
			fout = open(full_filename, 'wb+')

			file_content = ContentFile(image.read())

			# Iterate through the chunks.
			for chunk in file_content.chunks():
				fout.write(chunk)
			fout.close()

		# Data modifying operation - commit required
		if request.session["user_class"] == 'E':
			query = "INSERT INTO post_post('title', 'description', 'category', 'timestamp', 'updated', 'author_expert_id', 'image') Values(%s, %s, %s, %s, %s, %s, %s)"
		else:
			query = "INSERT INTO post_post('title', 'description', 'category', 'timestamp', 'updated', 'author_farmer_id', 'image') Values(%s, %s, %s, %s, %s, %s, %s)"

		if image:
			cursor.execute(query, [title, disc, category,  datetime.datetime.now(),  datetime.datetime.now(), current_user.auto_id, image.name])
		else:
			cursor.execute(query, [title, disc, category,  datetime.datetime.now(),  datetime.datetime.now(), current_user.auto_id, None])			
		transaction.commit()

		messages.success(request, "New Post Created")
		return redirect("home:welcome")

	context_data={
		"category" : POST_CATEGORIES,
	}
	return render(request,"create_edit_post.html",context_data)

def posts_detail(request,id=None):
	check = check_if_auth_user(request)
	current_user = None
	if check:
		cursor = connection.cursor()
		if request.session["user_class"] == 'E':
			query = "SELECT * FROM User_expert WHERE `User_expert`.'user_id' = %s"
		else:
			query = "SELECT * FROM User_farmer WHERE `User_farmer`.'user_id' = %s"

		cursor.execute(query, [check, ])
		result = namedtuplefetchall(cursor)
		current_user = result[0]

	if current_user is None:
		messages.error(request, "Perform Login first")
		return redirect("home:welcome")


	cursor = connection.cursor()
	query = "SELECT * FROM post_post WHERE `post_post`.'post_id' = %s"
	cursor.execute(query, [id, ])
	result = namedtuplefetchall(cursor)

	if not result:
		messages.error(request,"Given post was not found")
		return redirect("home:welcome")

	instance = result[0]

	author = None
	for elem in result:
		if elem.author_expert_id:
			query = "SELECT * FROM User_expert WHERE `User_expert`.'auto_id' = %s"
			cursor.execute(query, [elem.author_expert_id, ])
			result_ = namedtuplefetchall(cursor)
			author = result_[0]
		if elem.author_farmer_id:
			query = "SELECT * FROM User_farmer WHERE `User_farmer`.'auto_id' = %s"
			cursor.execute(query, [elem.author_farmer_id, ])
			result_ = namedtuplefetchall(cursor)
			author = result_[0]

	if request.method == "POST":
		cmnt = request.POST.get('comment')
		if request.session["user_class"] == 'F':
			messages.error(request, "Sorry, you cant comment here.")
			return redirect(reverse("post:detail", kwargs={ "id":id}))
		query = "INSERT INTO post_comment('timestamp', 'text', 'author_expert_id', 'post_id') VALUES(%s, %s, %s, %s)"
		cursor.execute(query, [datetime.datetime.now(),  cmnt, current_user.auto_id, id])			
		transaction.commit()

	query = "SELECT * FROM post_comment WHERE `post_comment`.'post_id' = %s"
	cursor.execute(query, [id, ])
	comments = namedtuplefetchall(cursor)

	comments_and_authors = []
	for comment in comments:
		query = "SELECT * FROM User_expert WHERE `User_expert`.'auto_id' = %s"
		cursor.execute(query, [comment.author_expert_id, ])
		result = namedtuplefetchall(cursor)
		comments_and_authors.append((comment, result[0]))

	context_data={
		"post_obj" : instance,
		"author" : author,
		"comments_and_authors": comments_and_authors,
	}
	return render(request, "view_post.html", context_data)


def posts_update(request,id=None):
	check = check_if_auth_user(request)
	current_user = None
	if check:
		cursor = connection.cursor()
		if request.session["user_class"] == 'E':
			query = "SELECT * FROM User_expert WHERE `User_expert`.'user_id' = %s"
		else:
			query = "SELECT * FROM User_farmer WHERE `User_farmer`.'user_id' = %s"

		cursor.execute(query, [check, ])
		result = namedtuplefetchall(cursor)
		current_user = result[0]

	if current_user is None:
		messages.error(request, "Perform Login first")
		return redirect("home:welcome")

	cursor = connection.cursor()
	query = "SELECT * FROM post_post WHERE `post_post`.'post_id' = %s"
	cursor.execute(query, [id, ])
	result = namedtuplefetchall(cursor)

	if not result:
		messages.error(request,"Given post was not found")
		return redirect("home:welcome")

	instance = result[0]

	if request.session["user_class"] == 'E':
		if current_user.auto_id != instance.author_expert_id:
			messages.error(request,"You can not edit this post!")
			return redirect(reverse("post:detail", kwargs={ "id":instance.post_id}))
	else:
		if current_user.auto_id != instance.author_farmer_id:
			messages.error(request,"You can not edit this post!")
			return redirect(reverse("post:detail", kwargs={ "id":instance.post_id}))

	if request.method == "POST":
		title = request.POST.get('post_title')
		disc = request.POST.get('post_disc')
		category = request.POST.get('post_category')
		try:
			image = request.FILES['post_image']
		except Exception:
			image = None

		if image:
			full_filename = os.path.join(MEDIA_ROOT, image.name)
			fout = open(full_filename, 'wb+')

			file_content = ContentFile(image.read())

			# Iterate through the chunks.
			for chunk in file_content.chunks():
				fout.write(chunk)
			fout.close()
		
		cursor = connection.cursor()

		# Data modifying operation - commit required
		
		if image:
			query = "UPDATE post_post SET 'title' = %s, 'description' = %s, 'category' = %s, 'updated' = %s, 'image' = %s WHERE `post_post`.'post_id' = %s"
			cursor.execute(query, [title, disc, category, datetime.datetime.now(), image.name, id])
		else:
			query = "UPDATE post_post SET 'title' = %s, 'description' = %s, 'category' = %s, 'updated' = %s, 'image' = NULL WHERE `post_post`.'post_id' = %s"
			cursor.execute(query, [title, disc, category, datetime.datetime.now(), id])
		transaction.commit()

		messages.success(request, "Your post was successfully updated.")
		return redirect(reverse("post:detail", kwargs={ "id":id}))

	context_data={
		"post_obj": instance,
		"category" : POST_CATEGORIES,
	}
	return render(request, "create_edit_post.html", context_data)


def posts_delete(request, id=None):
	check = check_if_auth_user(request)
	current_user = None
	if check:
		cursor = connection.cursor()
		if request.session["user_class"] == 'E':
			query = "SELECT * FROM User_expert WHERE `User_expert`.'user_id' = %s"
		else:
			query = "SELECT * FROM User_farmer WHERE `User_farmer`.'user_id' = %s"

		cursor.execute(query, [check, ])
		result = namedtuplefetchall(cursor)
		current_user = result[0]

	if current_user is None:
		messages.error(request, "Perform Login first")
		return redirect("home:welcome")

	cursor = connection.cursor()
	query = "SELECT * FROM post_post WHERE `post_post`.'post_id' = %s"
	cursor.execute(query, [id, ])
	result = namedtuplefetchall(cursor)

	if not result:
		messages.error(request,"Given post was not found")
		return redirect("home:welcome")

	instance = result[0]

	if request.session["user_class"] == 'E':
		if current_user.auto_id != instance.author_expert_id:
			messages.error(request,"You can not delete this post!")
			return redirect(reverse("post:detail", kwargs={ "id":instance.post_id}))
	else:
		if current_user.auto_id != instance.author_farmer_id:
			messages.error(request,"You can not delete this post!")
			return redirect(reverse("post:detail", kwargs={ "id":instance.post_id}))

	# Data modifying operation - commit required
	query = "DELETE from post_post WHERE `post_post`.'post_id' = %s"
	cursor.execute(query, [id,])
	transaction.commit()

	messages.success(request,"Post successfully deleted")
	return redirect("home:welcome")
