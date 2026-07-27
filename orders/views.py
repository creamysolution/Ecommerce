import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Order, OrderItem
from .forms import OrderCreateForm
from cart.cart import Cart

def order_create(request):
    cart = Cart(request)
    print(f"=== ORDER CREATE VIEW ===")
    print(f"Request method: {request.method}")
    print(f"Cart items: {len(cart)}")
    
    if not cart:
        print("Cart is empty, redirecting to cart_detail")
        return redirect('cart:cart_detail')
    
    if request.method == 'POST':
        print(f"POST data: {request.POST}")
        form = OrderCreateForm(request.POST)
        print(f"Form valid: {form.is_valid()}")
        
        if form.is_valid():
            try:
                order = form.save()
                print(f"Order saved: {order.id}")
                
                order_items_count = 0
                for item in cart:
                    print(f"Adding item: {item['product'].name}")
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['quantity']
                    )
                    order_items_count += 1
                
                print(f"Order items added: {order_items_count}")
                cart.clear()
                print(f"Cart cleared, redirecting to payment_process with order_id={order.id}")
                return redirect('orders:payment_process', order_id=order.id)
            except Exception as e:
                error = f"Error creating order: {str(e)}"
                print(error)
                import traceback
                traceback.print_exc()
                return render(request, 'orders/payment/error.html', {'error': error})
        else:
            print(f"Form is invalid. Errors: {form.errors}")
            return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})
    else:
        form = OrderCreateForm()
    
    return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})


def payment_process(request, order_id):
    print(f"\n=== PAYMENT PROCESS VIEW ===")
    print(f"Order ID: {order_id}")
    
    # Set Stripe API key
    if not settings.STRIPE_SECRET_KEY:
        error = 'Stripe API key not configured'
        print(f"ERROR: {error}")
        return render(request, 'orders/payment/error.html', {'error': error})
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    print(f"Stripe API key set: {settings.STRIPE_SECRET_KEY[:20]}...")
    
    order = get_object_or_404(Order, id=order_id)
    print(f"Order found: {order}")
    
    success_url = request.build_absolute_uri(reverse('orders:payment_completed'))
    cancel_url = request.build_absolute_uri(reverse('orders:payment_canceled'))
    print(f"Success URL: {success_url}")
    print(f"Cancel URL: {cancel_url}")

    # Stripe session data
    session_data = {
        'mode': 'payment',
        'success_url': success_url,
        'cancel_url': cancel_url,
        'line_items': []
    }

    # Add order items to the Stripe checkout session
    items_count = 0
    for item in order.items.all():
        price_in_cents = int(float(item.price) * 100)
        print(f"Item: {item.product.name}, Price: ${item.price}, Qty: {item.quantity}")
        session_data['line_items'].append({
            'price_data': {
                'unit_amount': price_in_cents,
                'currency': 'usd',
                'product_data': {
                    'name': item.product.name,
                },
            },
            'quantity': item.quantity,
        })
        items_count += 1
    
    print(f"Total items: {items_count}")

    try:
        print(f"Creating Stripe session...")
        session = stripe.checkout.Session.create(**session_data)
        print(f"Stripe session created successfully!")
        print(f"Session ID: {session.id}")
        print(f"Stripe URL: {session.url}")
        print(f"Redirecting to: {session.url}")
        return HttpResponseRedirect(session.url)
    except Exception as e:
        error_msg = f"Stripe Error: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return render(request, 'orders/payment/error.html', {'error': error_msg})

def payment_completed(request):
    return render(request, 'orders/payment/completed.html')

def payment_canceled(request):
    return render(request, 'orders/payment/canceled.html')