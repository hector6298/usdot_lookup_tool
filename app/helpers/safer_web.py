import logging
from flatten_dict import flatten
from safer import CompanySnapshot
from app.models.carrier_data import CarrierDataCreate

# Set up a module-level logger
logger = logging.getLogger(__name__)


def safer_web_lookup_from_dot(safer_client: CompanySnapshot,
                              dot_number: str) -> CarrierDataCreate:
    """Perform a safer web lookup using the dot reading."""
    try:
        logger.info(f"🔍 Performing SAFER web lookup for DOT number: {dot_number}")
        results = safer_client.get_by_usdot_number(int(dot_number))
        logger.info(results)
        if results:
            logger.info(f"✅ SAFER web lookup results found: {results}")

            results = results.to_dict()
            results.pop('us_inspections', None)
            results = flatten(results, reducer='underscore')

            result_record = CarrierDataCreate.model_validate(
                results,
                update={
                    "operation_classification": ', '.join(results.get("operation_classification", [])),
                    "carrier_operation": ', '.join(results.get("carrier_operation", [])),
                    "cargo_carried": ', '.join(results.get("cargo_carried", [])),
                    "lookup_success_flag": True,
                }
            )
            return result_record
        
    except Exception as e:
        logger.error(f"❌ SAFER web lookup failed: {e}")
        logger.warning("⚠ No data found for the provided DOT number.")
    
    # Default to empty record if no data found or error
    return CarrierDataCreate(usdot=dot_number, 
                             lookup_success_flag=False)
