import { useState } from "react";
import HeroSection from "./components/HeroSection";
import KuyaWidget from "./components/KuyaWidget";
import CalendarSection from "./components/CalendarSection";
import RoomsSection from "./components/RoomsSection";
import BookingConfirmation from "./components/BookingConfirmation";
import DirectionsSection from "./components/DirectionsSection";
import AboutSection from "./components/AboutSection";
import GallerySection from "./components/GallerySection";
import Footer from "./components/Footer";

export default function App() {
  const [activeSection, setActiveSection] = useState("idle");
  const [calendarHighlights, setCalendarHighlights] = useState(null);
  const [availableRooms, setAvailableRooms] = useState([]);
  const [bookingConfirmation, setBookingConfirmation] = useState(null);
  const [directionsData, setDirectionsData] = useState(null);

  return (
    <main>
      <HeroSection />
      <KuyaWidget
        setActiveSection={setActiveSection}
        setCalendarHighlights={setCalendarHighlights}
        setAvailableRooms={setAvailableRooms}
        setBookingConfirmation={setBookingConfirmation}
        setDirectionsData={setDirectionsData}
      />
      <CalendarSection highlights={calendarHighlights} isActive={activeSection === "calendar"} />
      <RoomsSection rooms={availableRooms} isActive={activeSection === "rooms"} />
      <BookingConfirmation booking={bookingConfirmation} isActive={activeSection === "confirmation"} />
      <DirectionsSection data={directionsData} isActive={activeSection === "directions"} />
      <AboutSection />
      <GallerySection />
      <Footer />
    </main>
  );
}
