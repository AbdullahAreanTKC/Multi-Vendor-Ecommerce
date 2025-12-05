from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import stripe
import json
from products.models import Cart
from django.conf import settings
from products.views import create_order_from_cart

# Create your views here.
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required(login_url="user_login")
def create_checkout_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    if not settings.STRIPE_SECRET_KEY:
        return JsonResponse({'error': 'Stripe secret key not configured'}, status=500)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)

    try:
        cart_products = Cart.objects.filter(user=request.user).values()
        cart_product_list = list(cart_products)

        if not cart_product_list:
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        # Serialize cart_product_list to JSON
        serialized_cart_products = json.dumps(cart_product_list, cls=DjangoJSONEncoder)

        subtotal = Cart.subtotal_product_price(request.user)
        amount = subtotal * 100

        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(amount),
            currency='usd',
            automatic_payment_methods={'enabled': True},
            metadata={'cart_products': serialized_cart_products},
        )

        return JsonResponse({'clientSecret': intent.client_secret})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=403)


# Display Payment Details with products
@login_required(login_url="user_login")
def display_payment_details(request):
    cart_products = Cart.objects.filter(user=request.user)
    if not cart_products:
        messages.error(request, "You have no items in your cart to pay for.")
        return redirect('show_cart')

    context = {
        'cart_products': cart_products,
        'payable': Cart.subtotal_product_price(request.user),
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'return_url': request.build_absolute_uri('/payment-success/'),
    }

    return render(request,'payments/payment.html', context)


@login_required(login_url="user_login")
def payment_success(request):
    payment_intent_id= request.GET.get('payment_intent')
    if not payment_intent_id:
        messages.error(request, "Missing payment information.")
        return redirect('display_payment_details')
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Stripe is not configured. Please contact support.")
        return redirect('display_payment_details')

    email = request.user.email
    try:
        order = create_order_from_cart(request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('show_cart')

    get_customer = stripe.Customer.search(query=f'email:"{email}"')
    if get_customer and get_customer.get('data'):
        customer = get_customer['data'][0]
    else:
        customer = stripe.Customer.create(
            name=request.user.first_name,
            email=request.user.email,
            description="Creating user for purchasing product"
        )

    payment_intent = stripe.PaymentIntent.modify(
        payment_intent_id,
        metadata={'order_id': order.oder_id},
        customer=customer
    )
    amount_paid = payment_intent['amount_received'] / 100

    context = {
        "payment_intent": payment_intent,
        "amount_paid": amount_paid
    }

    return render(request,'payments/success.html',context)