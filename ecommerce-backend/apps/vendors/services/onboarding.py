from apps.vendors.models import Vendor

def verify_vendor(vendor: Vendor) -> bool:
    """
    Performs verification checks on a vendor.
    Returns True if verification is successful, False otherwise.
    """
    if not vendor.business_name:
        return False
    
    # Check for required documents
    required_docs = ['gst', 'pan']
    uploaded_docs = vendor.documents.filter(doc_type__in=required_docs, file__isnull=False).values_list('doc_type', flat=True)
    
    # Check if all required docs are present
    missing_docs = set(required_docs) - set(uploaded_docs)
    
    if missing_docs:
        print(f"Verification failed for {vendor.business_name}. Missing docs: {missing_docs}")
        return False
        
    vendor.is_verified = True
    vendor.save(update_fields=['is_verified'])
    return True
