import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.models.organization import Organization
from app.models.user import User
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.campaign_lead import CampaignLead
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage

@pytest.mark.asyncio
async def test_relationships(async_session: AsyncSession):
    # org -> users
    org = Organization(name="Rel Org", slug="rel-org")
    user = User(email="test@rel.com", full_name="Test User", hashed_password="pwd", organization=org)
    
    # company -> people
    company = Company(name="Rel Co", organization=org)
    person = Person(first_name="Jane", last_name="Doe", organization=org, company=company)
    
    # person -> contacts
    contact = Contact(type="email", value="jane@rel.com", person=person)
    
    # company -> leads
    lead = Lead(organization=org, company=company, person=person)
    
    # campaign -> campaign_leads
    campaign = Campaign(name="Test Campaign", organization=org)
    campaign_lead = CampaignLead(campaign=campaign, lead=lead)
    
    # conversation -> messages
    conversation = Conversation(organization=org, lead=lead)
    message = ConversationMessage(conversation=conversation, content="Hello", direction="outbound", sequence_number=1)
    
    async_session.add_all([org, user, company, person, contact, lead, campaign, campaign_lead, conversation, message])
    await async_session.commit()
    
    # Test Org -> Users
    result_org = await async_session.execute(select(Organization).options(selectinload(Organization.users)).where(Organization.id == org.id))
    fetched_org = result_org.scalar_one()
    assert len(fetched_org.users) > 0
    assert fetched_org.users[0].full_name == "Test User"
    
    # Test Company -> People and Leads
    result_co = await async_session.execute(select(Company).options(selectinload(Company.people), selectinload(Company.leads)).where(Company.id == company.id))
    fetched_co = result_co.scalar_one()
    assert len(fetched_co.people) > 0
    assert len(fetched_co.leads) > 0
    
    # Test Person -> Contacts
    result_person = await async_session.execute(select(Person).options(selectinload(Person.contacts)).where(Person.id == person.id))
    fetched_person = result_person.scalar_one()
    assert len(fetched_person.contacts) > 0
    
    # Test Campaign -> CampaignLeads
    result_camp = await async_session.execute(select(Campaign).options(selectinload(Campaign.campaign_leads)).where(Campaign.id == campaign.id))
    fetched_camp = result_camp.scalar_one()
    assert len(fetched_camp.campaign_leads) > 0
    
    # Test Conversation -> Messages
    result_conv = await async_session.execute(select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation.id))
    fetched_conv = result_conv.scalar_one()
    assert len(fetched_conv.messages) > 0
