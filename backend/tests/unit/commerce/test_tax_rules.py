import pytest

from src.apps.commerce.models import Address, TaxRule
from src.apps.commerce.services import calculate_tax_amount


@pytest.mark.asyncio
async def test_calculate_tax_amount_prefers_matching_city_rule(db_session):
    address = Address(
        user_id=1,
        name="Home",
        phone="1234567890",
        line1="Street 1",
        city="Kathmandu",
        state="Bagmati",
        pincode="44600",
        country="Nepal",
    )

    db_session.add_all(
        [
            TaxRule(
                name="Bagmati Other City",
                country="Nepal",
                state="Bagmati",
                city="Lalitpur",
                rate=0.05,
                priority=1,
                is_active=True,
            ),
            TaxRule(
                name="Bagmati Kathmandu",
                country="Nepal",
                state="Bagmati",
                city="Kathmandu",
                rate=0.12,
                priority=2,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    result = await calculate_tax_amount(
        address=address,
        category_ids=set(),
        taxable_amount=100.0,
        db=db_session,
    )

    assert result["rule"] == "Bagmati Kathmandu"
    assert result["rate"] == 0.12
    assert result["tax"] == 12.0


@pytest.mark.asyncio
async def test_calculate_tax_amount_uses_default_when_no_rule_matches_city(db_session):
    address = Address(
        user_id=1,
        name="Home",
        phone="1234567890",
        line1="Street 1",
        city="Kathmandu",
        state="Bagmati",
        pincode="44600",
        country="Nepal",
    )

    db_session.add(
        TaxRule(
            name="Bagmati Lalitpur Rule",
            country="Nepal",
            state="Bagmati",
            city="Lalitpur",
            rate=0.2,
            priority=1,
            is_active=True,
        )
    )
    await db_session.commit()

    result = await calculate_tax_amount(
        address=address,
        category_ids=set(),
        taxable_amount=100.0,
        db=db_session,
    )

    assert result["rule"] == "default"
    assert result["rate"] == 0.13
    assert result["tax"] == 13.0


@pytest.mark.asyncio
async def test_calculate_tax_amount_city_match_is_case_insensitive(db_session):
    address = Address(
        user_id=1,
        name="Home",
        phone="1234567890",
        line1="Street 1",
        city="kathmandu",
        state="Bagmati",
        pincode="44600",
        country="Nepal",
    )

    db_session.add(
        TaxRule(
            name="Bagmati Kathmandu Mixed Case",
            country="Nepal",
            state="Bagmati",
            city="KaThMaNdU",
            rate=0.11,
            priority=1,
            is_active=True,
        )
    )
    await db_session.commit()

    result = await calculate_tax_amount(
        address=address,
        category_ids=set(),
        taxable_amount=100.0,
        db=db_session,
    )

    assert result["rule"] == "Bagmati Kathmandu Mixed Case"
    assert result["rate"] == 0.11
    assert result["tax"] == 11.0
