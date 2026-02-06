from celery import shared_task
import csv
import os
from django.db import transaction
from apps.catalog.models.category import Category
from apps.catalog.models.product import Product
from apps.catalog.models.product_variant import ProductVariant
from apps.vendors.models.vendor import Vendor
from apps.inventory.models.inventory import Inventory
from apps.inventory.models.warehouse import Warehouse

@shared_task
def process_bulk_upload(file_path, vendor_id):
    """
    Process a bulk product upload CSV file.
    Expected columns: name, category_slug, sku, price, stock, description
    """
    if not os.path.exists(file_path):
        return f"File {file_path} not found."

    success_count = 0
    errors = []

    try:
        vendor = Vendor.objects.get(id=vendor_id)
        # Ensure a warehouse exists for this vendor (or system default)
        warehouse, _ = Warehouse.objects.get_or_create(
            vendor=vendor,
            defaults={'name': f"{vendor.business_name} Main Warehouse", 'address': 'Default'}
        )

        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    with transaction.atomic():
                        # 1. Validate Category
                        category_slug = row.get('category_slug')
                        category = Category.objects.filter(slug=category_slug).first()
                        if not category:
                            raise ValueError(f"Category {category_slug} not found")

                        # 2. Get or Create Product
                        name = row.get('name')
                        product, _ = Product.objects.get_or_create(
                            vendor=vendor,
                            name=name,
                            defaults={
                                'category': category,
                                'description': row.get('description', ''),
                                'status': 'draft' # Default to draft for review
                            }
                        )
                        
                        # 3. Get or Create Variant
                        sku = row.get('sku')
                        price = float(row.get('price', 0))
                        variant, created = ProductVariant.objects.get_or_create(
                            product=product,
                            sku=sku,
                            defaults={
                                'name': name, # Default variant name same as product
                                'mrp': price * 1.2, # Mock MRP logic
                                'selling_price': price,
                                'is_default': not product.variants.exists()
                            }
                        )
                        
                        # 4. Update Inventory
                        stock = int(row.get('stock', 0))
                        Inventory.objects.update_or_create(
                            product_variant=variant,
                            warehouse=warehouse,
                            defaults={'quantity': stock, 'low_stock_threshold': 10}
                        )
                        
                        success_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing row {row.get('sku', 'unknown')}: {str(e)}")
                    
        return f"Processed upload for {vendor.business_name}. Success: {success_count}, Errors: {len(errors)}"
    except Vendor.DoesNotExist:
        return f"Vendor {vendor_id} not found."
    except Exception as e:
        return f"Failed to process file: {str(e)}"
