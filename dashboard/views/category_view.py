from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from topgrade_api.models import Category, Program
from .auth_view import admin_required

@admin_required
def edit_category_view(request, id):
    """Edit category view"""
    try:
        category = Category.objects.get(id=id)
    except Category.DoesNotExist:
        messages.error(request, 'Category not found')
        return redirect('dashboard:programs')
    
    if request.method == 'POST':
        # Handle Edit Category form
        name = request.POST.get('category_name')
        description = request.POST.get('category_description')
        icon = request.POST.get('category_icon')
        if name:
            category.name = name
            category.description = description
            category.icon = icon
            category.save()
            messages.success(request, 'Category updated successfully')
        else:
            messages.error(request, 'Category name is required')
        # Preserve pagination parameters when redirecting
        programs_page = request.GET.get('programs_page', 1)
        categories_page = request.GET.get('categories_page', 1)
        return redirect(f'/dashboard/programs/?programs_page={programs_page}&categories_page={categories_page}')
    
    # GET request - show edit form
    user = request.user
    categories_list = Category.objects.all().order_by('-id')
    programs_list = Program.objects.all().order_by('-id')
    
    # Programs Pagination
    programs_paginator = Paginator(programs_list, 9)
    programs_page = request.GET.get('programs_page')
    
    try:
        programs = programs_paginator.page(programs_page)
    except PageNotAnInteger:
        programs = programs_paginator.page(1)
    except EmptyPage:
        programs = programs_paginator.page(programs_paginator.num_pages)
    
    # Programs pagination range logic
    programs_current_page = programs.number
    programs_total_pages = programs_paginator.num_pages
    
    programs_start_page = max(1, programs_current_page - 1)
    programs_end_page = min(programs_total_pages, programs_current_page + 1)
    
    if programs_end_page - programs_start_page < 2:
        if programs_start_page == 1:
            programs_end_page = min(programs_total_pages, programs_start_page + 2)
        elif programs_end_page == programs_total_pages:
            programs_start_page = max(1, programs_end_page - 2)
    
    programs_page_range = range(programs_start_page, programs_end_page + 1)
    
    # Categories Pagination
    categories_paginator = Paginator(categories_list, 5)
    categories_page = request.GET.get('categories_page')
    
    try:
        categories = categories_paginator.page(categories_page)
    except PageNotAnInteger:
        categories = categories_paginator.page(1)
    except EmptyPage:
        categories = categories_paginator.page(categories_paginator.num_pages)
    
    # Categories pagination range logic
    categories_current_page = categories.number
    categories_total_pages = categories_paginator.num_pages
    
    categories_start_page = max(1, categories_current_page - 1)
    categories_end_page = min(categories_total_pages, categories_current_page + 1)
    
    if categories_end_page - categories_start_page < 2:
        if categories_start_page == 1:
            categories_end_page = min(categories_total_pages, categories_start_page + 2)
        elif categories_end_page == categories_total_pages:
            categories_start_page = max(1, categories_end_page - 2)
    
    categories_page_range = range(categories_start_page, categories_end_page + 1)
    
    context = {
        'user': user, 
        'categories': categories, 
        'programs': programs,
        'programs_page_range': programs_page_range,
        'programs_total_pages': programs_total_pages,
        'programs_current_page': programs_current_page,
        'categories_page_range': categories_page_range,
        'categories_total_pages': categories_total_pages,
        'categories_current_page': categories_current_page,
        'edit_category': category  # Pass the category to edit
    }
    return render(request, 'dashboard/programs.html', context)

@admin_required
def delete_category_view(request, id):
    """Delete category view""" 
    try:
        category = Category.objects.get(id=id)
        category.delete()
        messages.success(request, 'Category deleted successfully')
    except Category.DoesNotExist:
        messages.error(request, 'Category not found')
    # Preserve pagination parameters when redirecting
    programs_page = request.GET.get('programs_page', 1)
    categories_page = request.GET.get('categories_page', 1)
    return redirect(f'/dashboard/programs/?programs_page={programs_page}&categories_page={categories_page}')

