from django.shortcuts import render, redirect, HttpResponseRedirect
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import (Product, Industry, Cart, 
                     CustomerAddress, PlacedOder, 
                     PlacedeOderItem, CuponCodeGenaration, ProductStarRatingAndReview)
from . forms import CustomerAddressForm
import json
from accounts.models import CustomUser

# Create your views here.

def _get_cart_queryset_for_user(user):
    return Cart.objects.select_related("product", "shipping_address").filter(user=user)


def create_order_from_cart(user):
    """
    Create a placed order from the user's cart in an atomic and concurrency-safe way.
    Raises ValueError with a user-friendly message on failure.
    """
    with transaction.atomic():
        cart_items = _get_cart_queryset_for_user(user).select_for_update()
        if not cart_items:
            raise ValueError("Your cart is empty.")

        # Ensure a shipping address exists.
        shipping_address = cart_items.first().shipping_address
        if not shipping_address:
            raise ValueError("Please select a shipping address before placing an order.")

        sub_total_price = Cart.subtotal_product_price(user=user)
        order = PlacedOder.objects.create(
            user=user,
            shipping_address=shipping_address,
            sub_total_price=float(sub_total_price),
            paid=True,
        )

        for item in cart_items:
            product = Product.objects.select_for_update().get(id=item.product_id)
            if product.out_of_stoc or product.stoc < item.quantity:
                raise ValueError(f"{product.title} is out of stock.")
            product.stoc = product.stoc - item.quantity
            product.out_of_stoc = product.stoc <= 0
            product.save()

            PlacedeOderItem.objects.create(
                placed_oder=order,
                product=item.product,
                quantity=item.quantity,
                total_price=float(item.total_product_price),
            )
            item.delete()

        return order


def product_details(request, slug):
    product = get_object_or_404(Product, slug=slug)
    industry = Industry.objects.all()
    product_reviews = ProductStarRatingAndReview.objects.filter(product=product)
    context = {"product": product, "industry": industry,'product_reviews':product_reviews}
    return render(request, "products/product-details.html", context)


@login_required(login_url="user_login")
def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id)
    if not Cart.objects.filter(user=request.user, product=product).exists():
        Cart.objects.create(user=request.user, product=product)
    return redirect('show_cart')


@login_required(login_url="user_login")
def show_cart(request):
    carts = Cart.objects.filter(user=request.user)
    industry = Industry.objects.all()
    sub_total = 0.00
    if carts:
        sub_total = Cart.subtotal_product_price(user=request.user)
    context = {
        "carts": carts,
        "sub_total": format(sub_total, '.2f'),
        'industry':industry
        }
    return render(request, "products/cart.html", context)


@login_required(login_url="user_login")
@csrf_exempt
def increase_cart(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Invalid method"}, status=405)

    try:
        payload = json.loads(request.body)
        cart_id = int(payload.get("id"))
        action = int(payload.get("values"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"detail": "Invalid payload"}, status=400)

    products_list = []
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    carts_product = _get_cart_queryset_for_user(request.user)

    if action == 1 and cart_item.quantity < 50:
        cart_item.quantity += 1
        cart_item.save()
    elif action == 2 and cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    elif action == 0:
        cart_item.delete()
    else:
        return JsonResponse({"detail": "Unsupported action"}, status=400)

    for item in carts_product:
        product_details_dict = {}
        product_details_dict["id"] = item.product.id
        image_obj = item.product.productimage_set.first()
        product_details_dict["image"] = image_obj.image if image_obj else "https://placehold.co/200x200"
        product_details_dict["title"] = item.product.title
        product_details_dict["quantity"] = item.quantity
        product_details_dict["regular_price"] = float(item.product.discounted_price)
        product_details_dict["total_product_price"] = float(item.total_product_price)
        products_list.append(product_details_dict)

    sub_total = float(Cart.subtotal_product_price(user=request.user))
    data = {
        "product_quantity": cart_item.quantity if action != 0 else 0,
        "total_product_price": float(cart_item.total_product_price) if action != 0 else 0,
        "sub_total": sub_total,
        "carts_product": products_list or ["no-product"],
    }
    return JsonResponse(data)




# @login_required(login_url="user_login")
# def check_out(request):
#     user_cart = Cart.objects.filter(user=request.user)
#     all_shipping_address = CustomerAddress.objects.filter(user=request.user)
#     selected_shipping_address = CustomerAddress.objects.filter(user=request.user).last()
#     if user_cart:
#         industry = Industry.objects.all()
#         existing_address = CustomerAddress.objects.filter(user=request.user)
#         address_form = None
#         if request.method == 'POST':
#             user = request.user
#             if not existing_address.exists():
#                 address_form = CustomerAddressForm(data=request.POST)
#                 if address_form.is_valid():
#                     shipping_address = address_form.save(commit=False)
#                     shipping_address.user = user
#                     shipping_address.save()
#                     # print(shipping_address)
#             else:         
#                 shipping_address =  existing_address[0]
#                 address_form = CustomerAddressForm(data=request.POST)
#                 if address_form.is_valid():
#                         # getting addres raw data               
#                         city = address_form.cleaned_data['city']
#                         state = address_form.cleaned_data['state']
#                         zip_code = address_form.cleaned_data['zip_code']
#                         street_address = address_form.cleaned_data['street_address']
#                         mobile = address_form.cleaned_data['mobile']
#                         # saving Shipping address
#                         shipping_address.city = city
#                         shipping_address.state = state
#                         shipping_address.zip_code = zip_code
#                         shipping_address.street_address = street_address
#                         shipping_address.mobile = mobile
#                         shipping_address.save()

#             carts = Cart.objects.filter(user=user)
#             if carts.exists():
#                 place_order = PlacedOder.objects.create(
#                     user=user,
#                     shipping_address= shipping_address,
#                     sub_total_price = Cart.subtotal_product_price(user=user)
#                 )
#                 print(place_order)
#                 print("ITS IDDDDDDDD",place_order.id)
#                 # getting the all product of user Cart and save them to PlacedOderItem then remove from Cart
#                 for item in carts:
#                     # decrese product number from Product Model
#                     product_obj = Product.objects.get(id=item.product.id)
#                     if not item.product.out_of_stoc:
#                         if product_obj.stoc >= item.quantity:
#                             product_obj.stoc = product_obj.stoc - item.quantity
#                             if product_obj.stoc == 0:
#                                 product_obj.out_of_stoc = True
#                             product_obj.save()
#                         else:
#                             shipping_address.delete()
#                             # PlacedOder.objects.get(id=place_order.id).delete()
#                             messages.info(request,f"{product_obj.title[:20]} is avilable less than your quantity")
#                             return redirect('show_cart')
#                     else:
#                         shipping_address.delete()
#                         PlacedOder.objects.get(id=place_order.id).delete()
#                         messages.info(request,f"{product_obj.title[:20]} is currently out of stock")
#                         return redirect('show_cart')           
                    
#                     PlacedeOderItem.objects.create(
#                         placed_oder=place_order,
#                         product=item.product,
#                         quantity=item.quantity,
#                         total_price=item.total_product_price
#                     )
#                     item.delete()

#                 place_order.save()
#             messages.success(request, 'Your Order Placed SuccessFully!!!')
#             return redirect('user_dashboard')
            
#         # Removing Cupon Code
#         data = request.GET.get('remove_cupon')
#         carts = Cart.objects.filter(user=request.user)
#         if data: 
#             for item in carts:
#                 item.cupon_applaied = False
#                 item.cupon_code = None
#                 item.save()

#         cupon = False
#         if carts and carts[0].cupon_applaied:
#             cupon = True

#         #Calculate the subtotal after Removing the cupon code
#         sub_total = Cart.subtotal_product_price(user=request.user)

#         #checking the existing address and retur it to the template as form
#         if existing_address.exists():
#             address_form  = CustomerAddressForm(instance=existing_address[0])
#         else:       
#             address_form = CustomerAddressForm()

#         context ={'address_form':address_form,'cupon':cupon,'carts':carts,
#                 'sub_total':sub_total,
#                 'industry':industry,
#                 'all_shipping_address':all_shipping_address,
#                 'selected_shipping_address':selected_shipping_address
#                 }
#         return render(request,'products/checkout.html',context)
#     else:
#         messages.info(request,'You have no product in your Cart')
#         return redirect('home')




@login_required(login_url="user_login")
def check_out(request):
    user_cart = _get_cart_queryset_for_user(request.user)
    if not user_cart:
        messages.info(request, 'You have no product in your Cart')
        return redirect('home')

    all_shipping_address = CustomerAddress.objects.filter(user=request.user)
    first_cart_item = user_cart.first()
    selected_shipping_address = first_cart_item.shipping_address or all_shipping_address.last()

    if request.method == 'POST':
        selected_shipping_address_id = request.POST.get('selected_address_id')
        if selected_shipping_address_id:
            selected_shipping_address = get_object_or_404(
                CustomerAddress, id=selected_shipping_address_id, user=request.user
            )
            for item in user_cart:
                item.shipping_address = selected_shipping_address
                item.save(update_fields=["shipping_address"])

    # Removing Cupon Code
    if request.GET.get('remove_cupon'):
        for item in user_cart:
            item.cupon_applaied = False
            item.cupon_code = None
            item.save(update_fields=["cupon_applaied", "cupon_code"])

    cupon = bool(user_cart and user_cart[0].cupon_applaied)
    sub_total = Cart.subtotal_product_price(user=request.user)
    industry = Industry.objects.all()
    address_form = CustomerAddressForm()

    context = {
        'address_form': address_form,
        'cupon': cupon,
        'carts': user_cart,
        'sub_total': sub_total,
        'industry': industry,
        'all_shipping_address': all_shipping_address,
        'selected_shipping_address': selected_shipping_address
    }
    return render(request, 'products/checkout.html', context)



@login_required(login_url="user_login")
def placed_oder(request):
    try:
        order = create_order_from_cart(request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('show_cart')

    messages.success(request, 'Order placed successfully')
    return redirect('user_dashboard')


@login_required(login_url="user_login")
def cupon_apply(request):
    if request.method =='POST':
        cupon_code = request.POST.get('cupon_code')
        print(cupon_code)
        cupon_obj = CuponCodeGenaration.objects.filter(cupon_code=cupon_code)
        if cupon_obj.exists():
            subtotal = Cart.subtotal_product_price(user=request.user)
            user_carts = Cart.objects.filter(user=request.user)
            if not user_carts:
                messages.error(request, "No items found in cart to apply coupon.")
                return redirect('show_cart')

            less_amount_by_cupon = (subtotal * cupon_obj[0].discoun_parcent) / 100
            if less_amount_by_cupon <= cupon_obj[0].up_to:
                for item in user_carts:
                    item.cupon_code = cupon_obj[0]
                    item.cupon_applaied = True
                    item.save(update_fields=["cupon_code", "cupon_applaied"])
                messages.success(request, "Coupon applied successfully.")
            else:
                messages.error(request, "Coupon amount exceeds allowed discount limit.")
        else:
            messages.error(request, "Invalid coupon code.")
    return redirect('check_out')


def add_product_review_and_rating(request):
    if request.user.is_authenticated and request.user.user_role == '1':
        if request.method == 'POST':
            data = request.body
            data = json.loads(data)
            product_id = int(data.get('product_id'))
            stars = data.get('stars')
            review_messages = data.get('review_messages')

            # Geting the Product and User obj
            product_obj = Product.objects.get(id=product_id)
            user_obj = CustomUser.objects.get(id=request.user.id)
            if user_obj.user_role == '1':                   
                # Creting New Product Review
                product_review_instance = ProductStarRatingAndReview(
                    product=product_obj, user=user_obj, stars=stars, review_message=review_messages
                )
                product_review_instance.save()

                return JsonResponse({"status":200})
    else:
        messages.info(request,f"{request.user.first_name} is not a customer!!!")
        # print(request.META)
        current_page_url = request.META.get('HTTP_REFERER')
        print(current_page_url)
        # return product_details(request,current_page_url)
        return redirect('/')


# SRTIPE PAYMENTS VIEWS ---------------------->>

@login_required(login_url="user_login")
def save_shipping_address(request):
    if request.method == 'POST':
        new_address = CustomerAddressForm(data=request.POST)
        if new_address.is_valid():
            temp_new_address = new_address.save(commit=False)
            temp_new_address.user = request.user
            temp_new_address.save()
            user_cart = Cart.objects.filter(user=request.user)
            for item in user_cart:
                item.shipping_address = temp_new_address
                item.save(update_fields=["shipping_address"])
        else:
            messages.error(request, "Please correct the shipping address details.")
    return redirect('check_out')