from django.shortcuts import render
from .models import OrderItem
from .forms import OrderCreateForm
from cart.cart import Cart

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
            cart.clear()
            # Redirect to payment view
            return redirect('orders:payment_process', order_id=order.id)
    else:
        form = OrderCreateForm()
    return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})

import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY

def payment_process(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    success_url = request.build_absolute_uri(reverse('orders:payment_completed'))
    cancel_url = request.build_absolute_uri(reverse('orders:payment_canceled'))

    # Stripe session data
    session_data = {
        'mode': 'payment',
        'client_reference_id': order.id,
        'success_url': success_url,
        'cancel_url': cancel_url,
        'line_items': []
    }

    # Add order items to the Stripe checkout session
    for item in order.items.all():
        session_data['line_items'].append({
            'price_data': {
                'unit_amount': int(item.price * 100),  # Price in cents
                'currency': 'usd',
                'product_data': {
                    'name': item.product.name,
                },
            },
            'quantity': item.quantity,
        })

    session = stripe.checkout.Session.create(**session_data)
    return redirect(session.url, code=333)

def payment_completed(request):
    return render(request, 'orders/payment/completed.html')

def payment_canceled(request):
    return render(request, 'orders/payment/canceled.html')