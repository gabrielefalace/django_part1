from django.shortcuts import render
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, F, Count, Max, Min, Avg, Value, Func, ExpressionWrapper, DecimalField
from django.db.models.functions import Concat
from django.db.models.aggregates import Count
from django.db import transaction, connection
from django.contrib.contenttypes.models import ContentType
from store.models import Product, OrderItem, Order, Customer, Collection
from tags.models import TaggedItem

# Create your views here.
# request -> response
# request handler


def say_hello(request):
    #query_set = Product.objects.all()
    # query sets are evaluated when accessed, not when we e.g. call "all()" % Co.
    # unless are e.g. .count() which returns a number
    # .get(id=1) or even better .get(pk=1) not a query_set, but an object

    try:
        product = Product.objects.get(pk=1)
        print('PROD = \n', product.title)
    except ObjectDoesNotExist:
        pass

    # filter will return None is query_set is empty
    prod2 = Product.objects.filter(pk=2).first()
    print('PROD2 = \n', prod2.title)
    # also possible: filter(pk=2).exists() to get a boolean

    # Docs in QuerySet API Reference => Field Lookups
    products = Product.objects.filter(unit_price__range=(20, 30))
    # also cross-relation
    queryset = Product.objects.filter(Q(inventory__lt=10) & ~Q(unit_price__lt=20))

    queryset2 = Product.objects.filter(inventory=F('unit_price'))
    queryset3 = Product.objects.filter(inventory=F('collection__id'))

    queryset4 = Product.objects.filter(collection__id=3).order_by('unit_price', '-title') # unit_price ascending, then title descending

    single_element = Product.objects.order_by('unit_price', '-title')[0]
    print('Single Element = ', single_element.title)     # same: .earliest('unit_price') ==> also latest()

    #prod_in_collections = Product.objects.filter(title__icontains='coffee')

    limited = Product.objects.values('id','title','collection__title').all()[5:10]  # means [5,10) = 5, 6, 7, 8, 9
    # values_list(…) would return a set of Tuples

    ordered_by_title = Product.objects.filter(pk=F('orderitem__product_id')).order_by('title').distinct()
    ordered_by_title2 = Product.objects.filter(id__in=OrderItem.objects.values('product_id')).distinct().order_by('title')
    # instead of values(…), only(…) will return objects with only certain fields — defer(…) is the dual.
    # But if we access a field that was not in the initial projection, it'll issue (a multitude of) additional queries!

    # Select Related - When the other end is (1)
    related_selection = Product.objects.select_related('collection').all()

    # Prefetch Related - When the other end is (n)
    prefetched_selection = Product.objects.prefetch_related('promotions').select_related('collection').all()

    # Last 5 orders
    last_5_orders = Order.objects.select_related('customer').prefetch_related('orderitem_set__product').order_by('-placed_at')[:5]

    result = Product.objects.filter(collection__id=3).aggregate(some_count=Count('id'), min_price=Min('unit_price'))

    # Annotating objects lets you add fields as you fetch them; Pass in an expression obj like Value, F, Aggregate
    # qset = Customer.objects.annotate(is_new=Value(True))
    qset = Customer.objects.annotate(new_id=F('id')+1)    # same value as the primary key + 1

    #fullname_set = Customer.objects.annotate(full_name=Func(F('first_name'), Value(' '), F('last_name'), function='CONCAT'))
    fullname_set = Customer.objects.annotate(full_name=Concat('first_name', Value(' '), 'last_name'))

    # basically we count on order_set => for some strange reason "set" is not to be used!
    count_orders_set = Customer.objects.annotate(orders_count=Count('order'))
    count_orders_set[0]  # just to execute

    discount_exp = ExpressionWrapper(F('unit_price') * 0.8, output_field=DecimalField())
    discount_queryset = Product.objects.annotate(discounted_price=discount_exp)
    discount_queryset[0]

    tags_queryset = TaggedItem.objects.get_tags_for(Product, 1)


    # Creating a new Object (& DB Record)
    collection = Collection()
    collection.title = 'Video Games'
    collection.featured_product = Product(pk=1)
    # collection.featured_product_id = 1
    collection.save()  # insert cuz no ID provided

    # created_collection = Collection.objects.create(name='a', featured_product_id=1)


    collection2 = Collection.objects.get(pk=11)
    collection2.title = 'Gamees'
    collection2.featured_product = None
    collection2.save()

    # Faster update, in case we need performance boost (doesn't read from DB / ORM)
    Collection.objects\
        .filter(pk=11)\
        .update(featured_product=None)

    # !! DELETE !!
    #collection_to_delete = Collection(pk=11)
    #collection_to_delete.delete()


    # Transactions: wrap with @transaction.atomic() decorator on top of the func

    # First create the parent, then the child.

    with transaction.atomic():
        order = Order()
        order.customer_id = 1
        order.save()

        item = OrderItem()
        item.order = order
        item.product_id = 1
        item.quantity = 1
        item.unit_price = 10
        item.save()


    raw_queryset = Product.objects.raw('SELECT id, title FROM store_product')

    with connection.cursor() as cursor:
        cursor.execute('SELECT id, title FROM store_product')
        # cursor.callproc('get_customers', [1, 2, 'a'])

    # return HttpResponse('Hello Wold') # not HTML but simply data
    return render(request, 'hello.html', {'name': 'Gab', 'result': result, 'tags': list(tags_queryset)})