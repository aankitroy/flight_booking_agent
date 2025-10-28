import asyncio
from dotenv import load_dotenv
import random
from datetime import datetime, timedelta
from typing import Any
from google.genai import types

from livekit import agents
from livekit.agents import NOT_GIVEN, AgentSession, Agent, ChatContext, RoomInputOptions, RunContext, function_tool
from livekit.plugins import (
    openai,
    google,
    noise_cancellation,
)

load_dotenv(".env.local")


class FlightBookingAgent(Agent):
    def __init__(self, chat_ctx: ChatContext  | None = None) -> None:
        super().__init__(instructions="""You are a helpful flight booking AI assistant. You can help users book flights and also transfer them to hotel booking if needed.

If a user asks a question about flights, airlines, airports, travel policies, or need general information, use the search_knowledge_base tool to search the knowledge base and provide the information.

When a user wants to book a flight, ask them for:
1. Departure city/airport (source)
2. Destination city/airport (destination) 
3. Travel date

Then use the book_flight tool to complete their booking. If they also need hotel booking, use the transfer_to_hotel_booking tool. Be friendly, professional, and helpful.""", chat_ctx=chat_ctx if chat_ctx else NOT_GIVEN)
    

    async def _perform_search(self, query: str) -> str:
        """Perform a search in the knowledge base."""
        
        # Simulate a delay to represent actual searching
        await asyncio.sleep(2.0)
        # Provide some static information about flight policy
        policy_info = (
            "Flight Policy Info: Changes are allowed up to 24 hours before departure with a fee. "
            "Baggage allowance: 1 checked bag (23kg) and 1 cabin bag per passenger. "
            "For international flights, please arrive 2 hours before your scheduled departure."
        )
        return (
            f"Searching the knowledge base for \"{query}\"...\n\n"
            f"{policy_info}"
        )


    @function_tool()
    async def search_knowledge_base(
    self,
    context: RunContext,
    query: str,
    ) -> str:
        # Send a verbal status update to the user after a short delay
        """Search the knowledge base for relevant information.
        
        Args:
            query: The query to search the knowledge base for
        """
        
        async def _speak_status_update(delay: float = 0.5):
            await asyncio.sleep(delay)
            await context.session.generate_reply(instructions=f"""
                You are searching the knowledge base for \"{query}\" but it is taking a little while.
                Update the user on your progress, but be very brief.
            """)
        
        status_update_task = asyncio.create_task(_speak_status_update(2))

        # Perform search (function definition omitted for brevity)
        result = await self._perform_search(query)
        
        # Cancel status update if search completed before timeout
        status_update_task.cancel()
    
        return result

    @function_tool()
    async def book_flight(
        self,
        context: RunContext,
        source: str,
        destination: str,
        date: str,
    ) -> dict[str, Any]:
        """Book a flight from source to destination on a specific date.
        
        Args:
            source: Departure city/airport (e.g., 'New York', 'LAX', 'London')
            destination: Arrival city/airport (e.g., 'Los Angeles', 'JFK', 'Paris')
            date: Travel date (e.g., 'January 15, 2025', '2025-01-15', 'tomorrow')
        """
        # Generate simple flight details
        flight_number = f"FL{random.randint(1000, 9999)}"
        
        # Convert the date string to a departure date
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if "tomorrow" in date.lower():
            departure_date = today + timedelta(days=1)
        elif "today" in date.lower():
            departure_date = today
        elif "next week" in date.lower():
            departure_date = today + timedelta(days=7)
        else:
            # Try to parse specific dates
            try:
                # Handle formats like "18th Dec 2025", "Dec 18 2025", "18 Dec 2025"
                date_clean = date.lower().replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
                
                # Try different date formats
                formats = [
                    "%d %b %Y",      # "18 dec 2025"
                    "%b %d %Y",      # "dec 18 2025" 
                    "%d %B %Y",      # "18 december 2025"
                    "%B %d %Y",      # "december 18 2025"
                    "%Y-%m-%d",      # "2025-12-18"
                    "%m/%d/%Y",      # "12/18/2025"
                    "%d/%m/%Y",      # "18/12/2025"
                ]
                
                departure_date = None
                for fmt in formats:
                    try:
                        departure_date = datetime.strptime(date_clean, fmt)
                        break
                    except ValueError:
                        continue
                
                # If parsing failed, use fallback
                if departure_date is None:
                    departure_date = today + timedelta(days=random.randint(1, 30))
                    
            except Exception:
                # If anything goes wrong, use fallback
                departure_date = today + timedelta(days=random.randint(1, 30))
        departure_hour = random.randint(6, 22)  # Random hour between 6 AM and 10 PM
        departure_minute = random.choice([0, 15, 30, 45])  # Quarter hour intervals
        departure_time = departure_date.replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0)
        
        # Add random flight duration (2-8 hours)
        flight_duration = timedelta(hours=random.randint(2, 8))
        arrival_time = departure_time + flight_duration
        
        price = random.randint(200, 1000)
        seat = f"{random.choice(['A', 'B', 'C', 'D', 'E', 'F'])}{random.randint(1, 30)}"
        
        # Print booking details to console
        print(f"🛫 FLIGHT BOOKING CONFIRMED!")
        print(f"   Flight: {flight_number}")
        print(f"   Route: {source.upper()} → {destination.upper()}")
        print(f"   Date: {date}")
        print(f"   Departure: {departure_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Arrival: {arrival_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Price: ${price}")
        print(f"   Seat: {seat}")
        print(f"   Status: CONFIRMED ✅")
        print("-" * 50)
        
        # Return structured data
        return {
            "status": "confirmed",
            "flight_number": flight_number,
            "route": f"{source.upper()} → {destination.upper()}",
            "date": date,
            "departure": departure_time.strftime('%B %d, %Y at %I:%M %p'),
            "arrival": arrival_time.strftime('%B %d, %Y at %I:%M %p'),
            "price": f"${price}",
            "seat": seat,
            "message": f"Flight {flight_number} from {source} to {destination} on {date} has been successfully booked!"
        }
    
    @function_tool()
    async def transfer_to_hotel_booking(self, context: RunContext):
        """Transfer the user to a hotel booking specialist for hotel reservations."""
        return HotelBookingAgent(chat_ctx=self.chat_ctx)
    
    async def on_enter(self):
        """Agent becomes active - greet the user"""
        await self.session.generate_reply(
            instructions="""Greet the user and ask for their flight booking details which are not provided in the context.""")
    
    async def on_exit(self):
        pass


class HotelBookingAgent(Agent):
    def __init__(self, chat_ctx: ChatContext  | None = None) -> None:
        super().__init__(instructions="""You are a helpful hotel booking AI assistant. You can help users book hotels for their travel.
        
When a user wants to book a hotel, ask them for:
1. City/location where they need the hotel
2. Check-in date
3. Check-out date
4. Number of guests
5. Room preferences (optional)

Then use the book_hotel tool to complete their booking. Be friendly, professional, and helpful.""",  chat_ctx=chat_ctx if chat_ctx else NOT_GIVEN)
    
    def extract_flight_context(self) -> str:
        """Extract flight booking context from chat history and return formatted context info."""
        context_info = ""
        flight_details = {}
        
        if not self.chat_ctx:
            return context_info
            
        # Try to access messages if available
        if hasattr(self.chat_ctx, 'items'):
            print(f"📝 Number of messages: {len(self.chat_ctx.items)}")
            for i, item in enumerate(self.chat_ctx.items):
                if hasattr(item, 'role'):
                    print(f"  {item.role}: {item.content}")
                    
                    # Extract flight booking information from the conversation
                    if item.role == "user" and item.content:
                        content = str(item.content).lower()
                        # Look for flight booking details
                        if "flight" in content or "book" in content:
                            # Extract destination city
                            if "to " in content:
                                parts = content.split("to ")
                                if len(parts) > 1:
                                    destination = parts[1].split()[0]  # First word after "to"
                                    flight_details["destination"] = destination.title()
                            
                            # Extract date information
                            if any(word in content for word in ["tomorrow", "today", "next week", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]):
                                for word in ["tomorrow", "today", "next week", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]:
                                    if word in content:
                                        flight_details["date"] = word.title()
                                        break
                    
                    # Extract flight booking confirmation
                    if item.role == "assistant" and "flight" in str(item.content).lower() and "booked" in str(item.content).lower():
                        flight_details["confirmed"] = True
                        
        elif hasattr(self.chat_ctx, '__len__'):
            print(f"📝 Number of items: {len(self.chat_ctx.items)}")
        
        # Build context information for hotel booking
        if flight_details:
            context_info = f"""
IMPORTANT CONTEXT FROM FLIGHT BOOKING:
- The user has already booked a flight
- Destination: {flight_details.get('destination', 'Not specified')}
- Travel Date: {flight_details.get('date', 'Not specified')}
- Flight Status: {'Confirmed' if flight_details.get('confirmed') else 'In progress'}

Based on this information, suggest a hotel in the same destination city and around the same travel dates.
"""
        
        return context_info
    
    @function_tool()
    async def book_hotel(
        self,
        context: RunContext,
        city: str,
        check_in_date: str,
        check_out_date: str,
        guests: int,
        room_type: str = "standard",
    ) -> dict[str, Any]:
        """Book a hotel in a specific city for the given dates.
        
        Args:
            city: City where the hotel is located
            check_in_date: Check-in date (e.g., 'January 15, 2025', '2025-01-15', 'tomorrow')
            check_out_date: Check-out date (e.g., 'January 18, 2025', '2025-01-18', '3 days later')
            guests: Number of guests
            room_type: Type of room (standard, deluxe, suite, etc.)
        """
        # Generate simple hotel booking details
        hotel_name = f"Grand {city.title()} Hotel"
        confirmation_number = f"HT{random.randint(10000, 99999)}"
        
        # Simple pricing based on room type and duration
        base_price = 150 if room_type.lower() == "standard" else 250
        price_per_night = base_price + random.randint(50, 200)
        
        # Calculate number of nights (simplified)
        nights = random.randint(1, 7)  # For simplicity, random nights
        total_price = price_per_night * nights
        
        # Generate room number
        room_number = f"{random.randint(1, 20)}{random.choice(['A', 'B', 'C', 'D'])}"
        
        # Print booking details to console
        print(f"🏨 HOTEL BOOKING CONFIRMED!")
        print(f"   Hotel: {hotel_name}")
        print(f"   Location: {city.upper()}")
        print(f"   Check-in: {check_in_date}")
        print(f"   Check-out: {check_out_date}")
        print(f"   Guests: {guests}")
        print(f"   Room Type: {room_type.title()}")
        print(f"   Room Number: {room_number}")
        print(f"   Nights: {nights}")
        print(f"   Price per night: ${price_per_night}")
        print(f"   Total Price: ${total_price}")
        print(f"   Confirmation: {confirmation_number}")
        print(f"   Status: CONFIRMED ✅")
        print("-" * 50)
        
        # Return structured data
        return {
            "status": "confirmed",
            "hotel_name": hotel_name,
            "location": city.upper(),
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "guests": guests,
            "room_type": room_type.title(),
            "room_number": room_number,
            "nights": nights,
            "price_per_night": f"${price_per_night}",
            "total_price": f"${total_price}",
            "confirmation_number": confirmation_number,
            "message": f"Hotel {hotel_name} in {city} has been successfully booked for {guests} guests!"
        }
    
    async def on_enter(self):
        """Agent becomes active - greet the user"""
        # Print the received chat context
        print("🏨 HOTEL BOOKING AGENT ACTIVATED")
        print(f"📋 Received Chat Context: {self.chat_ctx}")
        
        # Extract flight context using the dedicated function
        context_info = self.extract_flight_context()
        
        print("-" * 50)
        
        await self.session.generate_reply(
            instructions=f"""Greet the user and ask for their hotel booking details which are not provided in the context:

{context_info}

Be friendly and helpful in collecting this information. If the user has already booked a flight, use that information to make relevant suggestions.""")
    
    async def on_exit(self):
        """Agent is exiting - say goodbye"""
        await self.session.generate_reply(
            instructions="Say a friendly goodbye and thank the user for their hotel booking.")


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Aoede",
            _gemini_tools=[types.GoogleSearch()],
        )
    )

    initial_ctx = ChatContext()
    initial_ctx.add_message(role="assistant", content=f"The user's name is Aankit Roy.")

    await session.start(
        room=ctx.room,
        agent=FlightBookingAgent(chat_ctx=initial_ctx),
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` instead for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )



if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))