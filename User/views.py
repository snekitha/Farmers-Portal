# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages

from django.db import connection, transaction

import datetime

# Create your views here.
from .models import start_user_session, check_if_auth_user, stop_user_session

from collections import namedtuple

def namedtuplefetchall(cursor):
	"Return all rows from a cursor as a namedtuple"
	desc = cursor.description
	nt_result = namedtuple('Result', [col[0] for col in desc])
	return [nt_result(*row) for row in cursor.fetchall()]

# Create your views here.
def view_profile(request):
	check = check_if_auth_user(request)
	current_user = None
	if not check:
		messages.error(request, "Log In to see your profile")
		return redirect("home:welcome")

	cursor = connection.cursor()
	if request.session["user_class"] == 'E':
		query = "SELECT * FROM User_expert WHERE `User_expert`.'user_id' = %s"
	else:
		query = "SELECT * FROM User_farmer WHERE `User_farmer`.'user_id' = %s"

	cursor.execute(query, [check, ])
	result = namedtuplefetchall(cursor)
	current_user = result[0]

	context_data = {
		'user': current_user,
	}

	return render(request, "profile.html", context_data)



def check_login(request):
	if check_if_auth_user(request):
		messages.error(request, "Log out to perform Log in")
		return redirect("home:welcome")

	temp_id = request.POST.get("email")
	temp_pwd = request.POST.get("passwd")
	
	context_data = {}
	
	if temp_pwd and temp_id:
		cursor = connection.cursor()
		query = "SELECT user_id, user_pwd, auto_id FROM User_expert"
		cursor.execute(query)
		result = namedtuplefetchall(cursor)

		for person in result:
			if person.user_id == temp_id:
				if person.user_pwd == temp_pwd:
					messages.success(request, "Successful Login")
					request = start_user_session(request, temp_id, 'E') # 'E' = Expert
					return redirect("home:welcome")
				else:
					messages.error(request, "Enter correct password")
					return redirect("home:welcome")

		cursor = connection.cursor()
		query = "SELECT user_id, user_pwd, auto_id FROM User_farmer"
		cursor.execute(query)
		result = namedtuplefetchall(cursor)

		for person in result:
			if person.user_id == temp_id:
				if person.user_pwd == temp_pwd:
					messages.success(request, "Successful Login")
					request = start_user_session(request, temp_id, 'F') # 'F' = Farmer
					return redirect("home:welcome")
				else:
					messages.error(request, "Enter correct password")
					return redirect("home:welcome")

		else:
			messages.error(request, "No such mail ID exists")

	return redirect("home:welcome")


def signup_user(request):
	if check_if_auth_user(request):
		messages.error(request, "Log out to perform sign up")
		return redirect("home:welcome")

	name = request.POST.get('user_name')
	email = request.POST.get('user_email')
	pwd = request.POST.get('user_passwd')
	con = request.POST.get('user_contact')
	city = request.POST.get('user_city')
	state = request.POST.get('user_state')
	category = request.POST.get('user_category')

	
	if name and email and pwd and city and state:
		cursor = connection.cursor()

		query = "SELECT loc_id FROM location_location WHERE `location_location`.city = %s and `location_location`.state = %s"
		cursor.execute(query, [city, state])
		result = namedtuplefetchall(cursor)
		if result:
			loc_id = result[0].loc_id
		else:
			# First insert city and state
			query = "INSERT INTO location_location ('city', 'state') Values(%s, %s)"
			cursor.execute(query, [city, state])
			transaction.commit()

			query = "SELECT loc_id FROM location_location WHERE `location_location`.city = %s and `location_location`.state = %s"
			cursor.execute(query, [city, state])
			result = namedtuplefetchall(cursor)
			loc_id = result[0].loc_id

		if category == 'Expert':
			query = "INSERT INTO User_expert('name', 'user_id', 'user_pwd', 'contact', 'location_id', 'join_timestamp') Values(%s, %s, %s, %s, %s, %s)"
		else:
			query = "INSERT INTO User_farmer('name', 'user_id', 'user_pwd', 'contact', 'location_id', 'join_timestamp') Values(%s, %s, %s, %s, %s, %s)"

		cursor.execute(query, [name, email, pwd, con, loc_id, datetime.datetime.now()])
		transaction.commit()
		
		messages.success(request, "Sign up was successful")
		messages.success(request, "Now you may login")

		return redirect("home:welcome")
	
	return render(request, "signup.html", {})

def logout_user(request):
	if stop_user_session(request):
		messages.success(request,"Logout Successful. Thank You for visiting")
		return redirect("home:welcome")
	else:
		messages.error(request,"Cant logout without any login")
		return redirect("home:welcome")