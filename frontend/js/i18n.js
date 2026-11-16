// Multilingual Localization Dictionary
// Supports English, Hindi, and Kannada

const translations = {
  en: {
    brand_title: "AgriLink Fleet & Vehicle Registry",
    brand_sub: "Commercial Fleet, Rental & Logistics Platform",
    tab_fleet: "Fleet Search & Booking",
    tab_owner: "Vehicle Owner Portal",
    tab_agrilink: "AgriLink Delivery Dispatch",
    tab_admin: "Admin & Official Console",
    tab_hub: "Microservice Integration Hub",
    
    actor_label: "Active Account:",
    lang_label: "Language:",
    
    search_placeholder: "Search vehicles by make, class, capacity or APMC market yard (or click mic)...",
    search_btn: "Search Fleet",
    voice_listening: "Listening... Speak your vehicle need (e.g. 'Tractor' or 'Tata Ace')",
    voice_prompt: "Click to speak search query",
    
    register_title: "Register New Commercial Vehicle",
    reg_no_label: "Registration Number",
    class_label: "Vehicle Class",
    make_model_label: "Make & Model",
    capacity_label: "Payload Capacity (kg)",
    fuel_label: "Fuel Type",
    rc_doc_label: "Registration Certificate (RC) Number",
    ocr_btn: "Auto-Fill via Smart OCR",
    submit_reg_btn: "Register Vehicle",
    
    my_vehicles: "My Fleet Vehicles",
    create_listing_title: "Publish Rental Listing & Rates",
    rate_hour: "Hourly Rate (₹)",
    rate_day: "Daily Rate (₹)",
    rate_km: "Per km Rate (₹)",
    security_deposit: "Security Deposit (₹)",
    pickup_loc: "Pickup APMC Yard / Hub Location",
    rental_rules: "Rental Rules & Driving Guidelines",
    publish_btn: "Publish Rental Listing",
    
    book_now_btn: "Book Vehicle",
    price_breakdown: "Rental Pricing & Security Deposit Breakdown",
    confirm_booking_btn: "Confirm Booking with Wallet Hold",
    overlap_guarantee: "Instant availability confirmation with double-booking protection",
    
    my_bookings: "My Active Bookings & Trips",
    handover_btn: "Start Trip (Handover)",
    return_btn: "End Trip & Settle",
    cancel_btn: "Cancel Booking",
    
    admin_queue_title: "Pending Vehicle Verifications",
    compliance_sweep_btn: "Run Fleet Safety & Compliance Scan",
    export_csv_btn: "Export Audit History (CSV)",
    export_registry_btn: "Export Vehicle Registry (CSV)",
    
    outbox_title: "Event Stream & Microservice Integrations",
    dispatch_outbox_btn: "Dispatch Pending Events",
    wallet_state_title: "Citizen Wallet & Active Holds",
    
    status_pending: "Pending Verification",
    status_verified: "Verified",
    status_available: "Available",
    status_reserved: "Reserved",
    status_rented: "On Trip (Rented)",
    status_intransit: "In Transit",
    status_maintenance: "Under Maintenance",
    status_suspended: "Suspended"
  },
  
  hi: {
    brand_title: "एग्रीलिंक फ्लीट व वाहन रजिस्ट्री",
    brand_sub: "व्यावसायिक फ्लीट, रेंटल व लॉजिस्टिक्स प्लेटफॉर्म",
    tab_fleet: "वाहन खोज व बुकिंग",
    tab_owner: "वाहन मालिक पोर्टल",
    tab_agrilink: "एग्रीलिंक डिलीवरी डिस्पैच",
    tab_admin: "प्रशासक व आधिकारिक कंसोल",
    tab_hub: "माइक्रोservice इंटीग्रेशन हब",
    
    actor_label: "सक्रिय खाता:",
    lang_label: "भाषा:",
    
    search_placeholder: "वाहन मॉडल, क्षमता या मंडी के अनुसार खोजें (या माइक बोलें)...",
    search_btn: "खोजें",
    voice_listening: "सुन रहे हैं... अपनी आवश्यकता बोलें (उदा. 'ट्रैक्टर' या 'टाटा ऐस')",
    voice_prompt: "बोलकर खोजने के लिए क्लिक करें",
    
    register_title: "नया व्यावसायिक वाहन पंजीकृत करें",
    reg_no_label: "पंजीकरण संख्या",
    class_label: "वाहन श्रेणी",
    make_model_label: "मेक व मॉडल",
    capacity_label: "भार वहन क्षमता (किग्रा)",
    fuel_label: "ईंधन प्रकार",
    rc_doc_label: "आरसी प्रमाण पत्र संख्या",
    ocr_btn: "स्मार्ट ओसीआर द्वारा स्वतः भरें",
    submit_reg_btn: "वाहन पंजीकृत करें",
    
    my_vehicles: "मेरे वाहन",
    create_listing_title: "किराया दर कार्ड व नियम निर्धारित करें",
    rate_hour: "दर / घंटा (₹)",
    rate_day: "दर / दिन (₹)",
    rate_km: "दर / किमी (₹)",
    security_deposit: "सुरक्षा जमा (₹)",
    pickup_loc: "पिकअप मंडी / केंद्र स्थल",
    rental_rules: "किराया नियम व ड्राइविंग दिशानिर्देश",
    publish_btn: "किराये के लिए उपलब्ध करें",
    
    book_now_btn: "वाहन बुक करें",
    price_breakdown: "किराया व वॉलेट होल्ड विवरण",
    confirm_booking_btn: "वॉलेट होल्ड के साथ पुष्टि करें",
    overlap_guarantee: "डबल-बुकिंग सुरक्षा के साथ तत्काल उपलब्धता पुष्टि",
    
    my_bookings: "मेरी सक्रिय बुकिंग व यात्राएं",
    handover_btn: "यात्रा शुरू करें (हैंडओवर)",
    return_btn: "वापसी व भुगतान निपटान",
    cancel_btn: "बुकिंग रद्द करें",
    
    admin_queue_title: "लंबित वाहन सत्यापन",
    compliance_sweep_btn: "फ्लीट सुरक्षा व वैधता जांच चलाएं",
    export_csv_btn: "ऑडिट रिकॉर्ड निर्यात करें (CSV)",
    export_registry_btn: "वाहन रजिस्ट्री निर्यात करें (CSV)",
    
    outbox_title: "इवेंट स्ट्रीम व माइक्रोservice इंटीग्रेशन",
    dispatch_outbox_btn: "लंबित इवेंट्स प्रसारित करें",
    wallet_state_title: "नागरिक वॉलेट व सक्रिय फंड होल्ड",
    
    status_pending: "सत्यापन लंबित",
    status_verified: "सत्यापित",
    status_available: "उपलब्ध",
    status_reserved: "आरक्षित",
    status_rented: "यात्रा पर (किराए पर)",
    status_intransit: "पारगमन में",
    status_maintenance: "रखरखाव में",
    status_suspended: "निलंबित"
  },
  
  kn: {
    brand_title: "ಅಗ್ರಿಲಿಂಕ್ ಫ್ಲೀಟ್ ಮತ್ತು ವಾಹನ ನೋಂದಣಿ",
    brand_sub: "ವಾಣಿಜ್ಯ ಫ್ಲೀಟ್, ಬಾಡಿಗೆ ಮತ್ತು ಲಾಜಿಸ್ಟಿಕ್ಸ್ ವೇದಿಕೆ",
    tab_fleet: "ವಾಹನ ಹುಡುಕಾಟ ಮತ್ತು ಬುಕಿಂಗ್",
    tab_owner: "ವಾಹನ ಮಾಲೀಕರ ಪೋರ್ಟಲ್",
    tab_agrilink: "ಅಗ್ರಿಲಿಂಕ್ ವಿತರಣಾ ರವಾನೆ",
    tab_admin: "ಆಡಳಿತ ಮತ್ತು ಅಧಿಕೃತ ಕನ್ಸೋಲ್",
    tab_hub: "ಮೈಕ್ರೋಸರ್ವಿಸ್ ಏಕೀಕರಣ ಹಬ್",
    
    actor_label: "ಸಕ್ರಿಯ ಖಾತೆ:",
    lang_label: "ಭಾಷೆ:",
    
    search_placeholder: "ಮಾದರಿ, ತೂಕ ಸಾಮರ್ಥ್ಯ ಅಥವಾ ಮಂಡಿ ಸ್ಥಳದ ಮೂಲಕ ಹುಡುಕಿ (ಧ್ವನಿ ಬಳಸಿ)...",
    search_btn: "ಹುಡುಕಿ",
    voice_listening: "ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇವೆ... ಮಾತನಾಡಿ (ಉದಾ: 'ಟ್ರಾಕ್ಟರ್' ಅಥವಾ 'ಟಾಟಾ ಏಸ್')",
    voice_prompt: "ಧ್ವನಿ ಮೂಲಕ ಹುಡುಕಲು ಕ್ಲಿಕ್ ಮಾಡಿ",
    
    register_title: "ಹೊಸ ವಾಣಿಜ್ಯ ವಾಹನ ನೋಂದಣಿ",
    reg_no_label: "ನೋಂದಣಿ ಸಂಖ್ಯೆ",
    class_label: "ವಾಹನ ವರ್ಗ",
    make_model_label: "ತಯಾರಕ ಮತ್ತು ಮಾದರಿ",
    capacity_label: "ತೂಕ ಸಾಮರ್ಥ್ಯ (ಕೆಜಿ)",
    fuel_label: "ಇಂಧನ ಪ್ರಕಾರ",
    rc_doc_label: "ಆರ್‌ಸಿ ಪ್ರಮಾಣಪತ್ರ ಸಂಖ್ಯೆ",
    ocr_btn: "ಸ್ಮಾರ್ಟ್ ಒಸಿಆರ್ ಮೂಲಕ ಭರ್ತಿ ಮಾಡಿ",
    submit_reg_btn: "ವಾಹನ ನೋಂದಾಯಿಸಿ",
    
    my_vehicles: "ನನ್ನ ವಾಹನಗಳು",
    create_listing_title: "ಬಾಡಿಗೆ ದರ ಮತ್ತು ನಿಯಮಗಳು",
    rate_hour: "ದರ / ಗಂಟೆಗೆ (₹)",
    rate_day: "ದರ / ದಿನಕ್ಕೆ (₹)",
    rate_km: "ದರ / ಕಿಮೀ (₹)",
    security_deposit: "ಭದ್ರತಾ ಠೇವಣಿ (₹)",
    pickup_loc: "ಪಿಕಪ್ ಮಂಡಿ / ತಾಣ",
    rental_rules: "ಬಾಡಿಗೆ ನಿಯಮಗಳು ಮತ್ತು ಚಾಲನಾ ಮಾರ್ಗಸೂಚಿಗಳು",
    publish_btn: "ಬಾಡಿಗೆಗೆ ಪ್ರಕಟಿಸಿ",
    
    book_now_btn: "ವಾಹನ ಬುಕ್ ಮಾಡಿ",
    price_breakdown: "ದರ ಮತ್ತು ವಾಲೆಟ್ ಹೋಲ್ಡ್ ವಿವರ",
    confirm_booking_btn: "ವಾಲೆಟ್ ಹೋಲ್ಡ್ ಮೂಲಕ ಖಚಿತಪಡಿಸಿ",
    overlap_guarantee: "ಡಬಲ್-ಬುಕಿಂಗ್ ರಕ್ಷಣೆಯೊಂದಿಗೆ ತಕ್ಷಣದ ಲಭ್ಯತೆ",
    
    my_bookings: "ನನ್ನ ಸಕ್ರಿಯ ಬುಕಿಂಗ್‌ಗಳು ಮತ್ತು ಪ್ರವಾಸಗಳು",
    handover_btn: "ಪ್ರವಾಸ ಪ್ರಾರಂಭಿಸಿ (ಹ್ಯಾಂಡ್‌ಓವರ್)",
    return_btn: "ಪ್ರವಾಸ ಮುಕ್ತಾಯ ಮತ್ತು ಇತ್ಯರ್ಥ",
    cancel_btn: "ಬುಕಿಂಗ್ ರದ್ದುಮಾಡಿ",
    
    admin_queue_title: "ಬಾಕಿ ಉಳಿದಿರುವ ವಾಹನ ಪರಿಶೀಲನೆಗಳು",
    compliance_sweep_btn: "ಫ್ಲೀಟ್ ಸುರಕ್ಷತೆ ಮತ್ತು ಮಾನ್ಯತೆ ತಪಾಸಣೆ",
    export_csv_btn: "ಆಡಿಟ್ ದಾಖಲೆ ರಫ್ತು (CSV)",
    export_registry_btn: "ವಾಹನ ನೋಂದಣಿ ರಫ್ತು (CSV)",
    
    outbox_title: "ಈವೆಂಟ್ ಸ್ಟ್ರೀಮ್ ಮತ್ತು ಮೈಕ್ರೋಸರ್ವಿಸ್ ಸಂಪರ್ಕ",
    dispatch_outbox_btn: "ಬಾಕಿ ಈವೆಂಟ್‌ಗಳನ್ನು ಪ್ರಸಾರ ಮಾಡಿ",
    wallet_state_title: "ನಾಗರಿಕ ವಾಲೆಟ್ ಮತ್ತು ಸಕ್ರಿಯ ಹೋಲ್ಡ್‌ಗಳು",
    
    status_pending: "ಪರಿಶೀಲನೆ ಬಾಕಿ",
    status_verified: "ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
    status_available: "ಲಭ್ಯವಿದೆ",
    status_reserved: "ಕಾಯ್ದಿರಿಸಲಾಗಿದೆ",
    status_rented: "ಪ್ರವಾಸದಲ್ಲಿದೆ (ಬಾಡಿಗೆ)",
    status_intransit: "ಸಾಗಣೆಯಲ್ಲಿದೆ",
    status_maintenance: "ದುರಸ್ತಿಯಲ್ಲಿದೆ",
    status_suspended: "ಅಮಾನತುಗೊಳಿಸಲಾಗಿದೆ"
  }
};

let currentLang = "en";

function setLanguage(lang) {
  if (translations[lang]) {
    currentLang = lang;
    applyTranslations();
  }
}

function t(key) {
  const dict = translations[currentLang] || translations["en"];
  return dict[key] || translations["en"][key] || key;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (key && t(key)) {
      el.textContent = t(key);
    }
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (key && t(key)) {
      el.placeholder = t(key);
    }
  });
  document.querySelectorAll("[data-i18n-title]").forEach(el => {
    const key = el.getAttribute("data-i18n-title");
    if (key && t(key)) {
      el.title = t(key);
    }
  });
}
