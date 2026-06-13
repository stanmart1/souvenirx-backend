from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.delivery import DeliveryZone, ShippingMethod, ShippingCarrier, ShippingAutomationRule
from app.data.west_africa_geography import WEST_AFRICA_COUNTRIES

router = APIRouter()


@router.get("/geography")
async def get_geography_data():
    """Get West Africa geographic data for dropdowns."""
    return WEST_AFRICA_COUNTRIES


@router.get("/zones")
async def list_delivery_zones(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeliveryZone).where(DeliveryZone.is_active == True))
    zones = result.scalars().all()
    return [
        {
            "id": z.id,
            "zone": z.zone_name,
            "states": z.states,
            "standard": z.standard_fee,
            "express": z.express_fee,
            "eta": z.eta_text,
            "min_days": z.min_days,
            "max_days": z.max_days,
            "free_shipping_threshold": z.free_shipping_threshold,
            "weight_fee_per_kg": z.weight_fee_per_kg,
            "volume_fee_per_unit": z.volume_fee_per_unit,
            "default_carrier": z.default_carrier,
            "auto_assign": z.auto_assign,
        }
        for z in zones
    ]


@router.get("/zones/detect")
async def detect_delivery_zone(
    country: str = "Nigeria",
    state: Optional[str] = None,
    lga: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Auto-detect delivery zone based on hierarchical geography (country > state > LGA)."""
    
    # Build query conditions
    conditions = [DeliveryZone.is_active == True]
    
    # Match country
    conditions.append(DeliveryZone.countries.contains([country]))
    
    # Match state if provided
    if state:
        conditions.append(DeliveryZone.states.contains([state]))
    
    # Match LGA if provided (for more granular zones)
    if lga:
        conditions.append(DeliveryZone.lgas.contains([lga]))
    
    # Query zones
    result = await db.execute(
        select(DeliveryZone).where(*conditions)
    )
    zones = result.scalars().all()
    
    if not zones:
        raise HTTPException(status_code=404, detail="No delivery zone found for this location")
    
    # Return the most specific zone (LGA > State > Country)
    # Sort by specificity: lga zones first, then state zones, then country zones
    zones_sorted = sorted(zones, key=lambda z: (
        0 if z.zone_type == "lga" else 1 if z.zone_type == "state" else 2
    ))
    
    zone = zones_sorted[0]
    
    return {
        "id": zone.id,
        "zone": zone.zone_name,
        "zone_type": zone.zone_type,
        "countries": zone.countries,
        "states": zone.states,
        "lgas": zone.lgas,
        "standard": zone.standard_fee,
        "express": zone.express_fee,
        "eta": zone.eta_text,
        "min_days": zone.min_days,
        "max_days": zone.max_days,
        "free_shipping_threshold": zone.free_shipping_threshold,
        "is_international": zone.is_international,
        "customs_handling_fee": zone.customs_handling_fee,
        "border_crossing_fee": zone.border_crossing_fee,
    }


@router.get("/zones/{zone_id}")
async def get_delivery_zone(zone_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DeliveryZone).where(DeliveryZone.id == zone_id, DeliveryZone.is_active == True)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Delivery zone not found")
    
    return {
        "id": zone.id,
        "zone": zone.zone_name,
        "states": zone.states,
        "standard": zone.standard_fee,
        "express": zone.express_fee,
        "eta": zone.eta_text,
        "min_days": zone.min_days,
        "max_days": zone.max_days,
        "free_shipping_threshold": zone.free_shipping_threshold,
        "weight_fee_per_kg": zone.weight_fee_per_kg,
        "volume_fee_per_unit": zone.volume_fee_per_unit,
    }


@router.get("/methods")
async def list_shipping_methods(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ShippingMethod).where(ShippingMethod.is_active == True).order_by(ShippingMethod.sort_order))
    methods = result.scalars().all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "base_fee": m.base_fee,
            "free_above_amount": m.free_above_amount,
            "fee_per_kg": m.fee_per_kg,
            "fee_per_item": m.fee_per_item,
            "min_days": m.min_days,
            "max_days": m.max_days,
            "carrier": m.carrier,
            "auto_select_for_zones": m.auto_select_for_zones,
            "max_weight_kg": m.max_weight_kg,
            "max_items": m.max_items,
        }
        for m in methods
    ]


@router.get("/methods/auto-select")
async def auto_select_shipping_method(
    zone_id: int,
    order_total: int,
    total_weight: Optional[float] = 0,
    total_items: Optional[int] = 0,
    db: AsyncSession = Depends(get_db),
):
    """Auto-select best shipping method based on rules and conditions."""
    
    # Get shipping methods that auto-select for this zone
    result = await db.execute(
        select(ShippingMethod).where(
            ShippingMethod.is_active == True,
            ShippingMethod.auto_select_for_zones.contains([zone_id])
        ).order_by(ShippingMethod.sort_order)
    )
    methods = result.scalars().all()
    
    # Filter by constraints
    eligible_methods = []
    for method in methods:
        # Check weight constraint
        if method.max_weight_kg and total_weight > method.max_weight_kg:
            continue
        # Check item constraint
        if method.max_items and total_items > method.max_items:
            continue
        eligible_methods.append(method)
    
    if not eligible_methods:
        # Fallback to first available method
        result = await db.execute(
            select(ShippingMethod).where(ShippingMethod.is_active == True).order_by(ShippingMethod.sort_order).limit(1)
        )
        method = result.scalar_one_or_none()
        if not method:
            raise HTTPException(status_code=404, detail="No shipping methods available")
        return {
            "id": method.id,
            "name": method.name,
            "base_fee": method.base_fee,
            "reason": "fallback",
        }
    
    # Select best method (lowest cost that meets requirements)
    best_method = min(eligible_methods, key=lambda m: m.base_fee)
    
    return {
        "id": best_method.id,
        "name": best_method.name,
        "base_fee": best_method.base_fee,
        "carrier": best_method.carrier,
        "reason": "auto_selected",
    }


@router.post("/calculate-shipping")
async def calculate_shipping(
    zone_id: int,
    order_total: int,
    total_weight: Optional[float] = 0,
    total_items: Optional[int] = 0,
    shipping_method_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Calculate shipping cost based on zone, order value, weight, and items."""
    
    # Get delivery zone
    result = await db.execute(
        select(DeliveryZone).where(DeliveryZone.id == zone_id, DeliveryZone.is_active == True)
    )
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Delivery zone not found")
    
    # Use shipping method if specified, otherwise use zone standard
    if shipping_method_id:
        result = await db.execute(
            select(ShippingMethod).where(ShippingMethod.id == shipping_method_id, ShippingMethod.is_active == True)
        )
        method = result.scalar_one_or_none()
        if not method:
            raise HTTPException(status_code=404, detail="Shipping method not found")
        
        base_fee = method.base_fee
        free_threshold = method.free_above_amount
        weight_fee = method.fee_per_kg
        item_fee = method.fee_per_item
        min_days = method.min_days
        max_days = method.max_days
    else:
        base_fee = zone.standard_fee
        free_threshold = zone.free_shipping_threshold
        weight_fee = zone.weight_fee_per_kg
        item_fee = zone.volume_fee_per_unit
        min_days = zone.min_days
        max_days = zone.max_days
    
    # Check for free shipping
    if free_threshold > 0 and order_total >= free_threshold:
        shipping_cost = 0
    else:
        shipping_cost = base_fee
        # Add weight-based fee
        if weight_fee > 0 and total_weight > 0:
            shipping_cost += int(total_weight * weight_fee)
        # Add item-based fee
        if item_fee > 0 and total_items > 0:
            shipping_cost += total_items * item_fee
        # Add international fees
        if zone.is_international:
            shipping_cost += zone.customs_handling_fee
            shipping_cost += zone.border_crossing_fee
    
    return {
        "shipping_cost": shipping_cost,
        "is_free": shipping_cost == 0,
        "estimated_days": f"{min_days}-{max_days} business days",
        "min_days": min_days,
        "max_days": max_days,
        "suggested_carrier": zone.default_carrier,
        "is_international": zone.is_international,
        "customs_fee": zone.customs_handling_fee if zone.is_international else 0,
        "border_fee": zone.border_crossing_fee if zone.is_international else 0,
    }


@router.get("/carriers")
async def list_carriers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ShippingCarrier).where(ShippingCarrier.is_active == True))
    carriers = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "auto_create_labels": c.auto_create_labels,
            "auto_schedule_pickup": c.auto_schedule_pickup,
            "auto_track_shipments": c.auto_track_shipments,
        }
        for c in carriers
    ]


@router.get("/automation-rules")
async def list_automation_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ShippingAutomationRule).where(ShippingAutomationRule.is_active == True).order_by(ShippingAutomationRule.priority.desc())
    )
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "rule_type": r.rule_type,
            "priority": r.priority,
            "conditions": r.conditions,
            "actions": r.actions,
        }
        for r in rules
    ]


@router.post("/apply-automation")
async def apply_automation_rules(
    state: str,
    order_total: int,
    total_weight: Optional[float] = 0,
    total_items: Optional[int] = 0,
    db: AsyncSession = Depends(get_db),
):
    """Apply automation rules to determine zone, method, and carrier."""
    
    result = await db.execute(
        select(ShippingAutomationRule).where(ShippingAutomationRule.is_active == True).order_by(ShippingAutomationRule.priority.desc())
    )
    rules = result.scalars().all()
    
    result_data = {
        "zone_id": None,
        "method_id": None,
        "carrier": None,
        "applied_rules": [],
    }
    
    for rule in rules:
        # Check if conditions match
        conditions_met = True
        for key, value in rule.conditions.items():
            if key == "min_order_value" and order_total < value:
                conditions_met = False
                break
            elif key == "max_order_value" and order_total > value:
                conditions_met = False
                break
            elif key == "max_weight" and total_weight > value:
                conditions_met = False
                break
            elif key == "max_items" and total_items > value:
                conditions_met = False
                break
            elif key == "state" and state != value:
                conditions_met = False
                break
        
        if conditions_met:
            result_data["applied_rules"].append(rule.name)
            # Apply actions
            if "assign_zone_id" in rule.actions:
                result_data["zone_id"] = rule.actions["assign_zone_id"]
            if "assign_method_id" in rule.actions:
                result_data["method_id"] = rule.actions["assign_method_id"]
            if "assign_carrier" in rule.actions:
                result_data["carrier"] = rule.actions["assign_carrier"]
    
    # Auto-detect zone if not assigned by rules
    if not result_data["zone_id"]:
        result = await db.execute(
            select(DeliveryZone).where(
                DeliveryZone.is_active == True,
                DeliveryZone.states.contains([state])
            )
        )
        zone = result.scalar_one_or_none()
        if zone:
            result_data["zone_id"] = zone.id
    
    return result_data


@router.get("/estimate")
async def estimate_delivery(
    category_slug: str = Query(...),
    quantity: int = Query(..., ge=1),
    zone_id: Optional[int] = Query(default=None),
    state: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Estimate delivery window for a given category, quantity, and zone/state."""
    zone_min: int = 3
    zone_max: int = 7

    if zone_id is not None:
        # Look up zone directly by ID
        zone_result = await db.execute(
            select(DeliveryZone).where(DeliveryZone.id == zone_id, DeliveryZone.is_active == True)
        )
        zone = zone_result.scalar_one_or_none()
        if zone:
            zone_min = zone.min_days
            zone_max = zone.max_days
    elif state is not None:
        # Detect zone by state
        zone_result = await db.execute(
            select(DeliveryZone).where(
                DeliveryZone.is_active == True,
                DeliveryZone.states.contains([state]),
            )
        )
        zone = zone_result.scalars().first()
        if zone:
            zone_min = zone.min_days
            zone_max = zone.max_days

    try:
        from app.services.delivery_time import estimate_delivery_window
        return estimate_delivery_window(category_slug, quantity, zone_min, zone_max)
    except ImportError:
        # Fallback when delivery_time service is not yet available
        total_min = zone_min + 2
        total_max = zone_max + 3
        return {
            "total_min": total_min,
            "total_max": total_max,
            "label": f"{total_min}–{total_max} business days",
            "category_slug": category_slug,
            "quantity": quantity,
            "production_days": 2,
            "shipping_min": zone_min,
            "shipping_max": zone_max,
        }
