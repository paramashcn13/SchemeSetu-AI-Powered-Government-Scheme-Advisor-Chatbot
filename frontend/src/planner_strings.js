/* English strings for the 6.5 / 6.6 / 6.7 UI.

   They live here, not in i18n.js, so this change doesn't touch your translation
   file. `pt(t, key, params)` asks the normal translator first; if i18n.js has no
   entry for the key (makeT returns the key itself, the same trick reasonText()
   uses) it falls back to the English below. To translate later, copy these keys
   into i18n.js for each language and nothing else needs to change. */

const EN = {
  // theme
  themeDark: "Switch to dark mode",
  themeLight: "Switch to light mode",

  // stop / resend
  stopped: "Stopped. Resend the question when you're ready.",
  stopLabel: "Stop",

  // source cards
  srcRecord: "Government scheme record",
  srcPage: "Page",
  srcOfficial: "View official page",
  srcDataAsOf: "Data as of {date}",

  // 6.6 life events
  eventsLabel: "Something just happened?",
  eventsHint: "Pick a life event and see schemes that may help.",
  eventCheckPrefix: "Life event",
  eventFieldLabel: "Life event (optional)",
  eventNone: "None",
  eventCaption: "Schemes for this life event",

  // 6.5 document planner
  docsToggle: "Documents you'll need",
  docsHide: "Hide documents",
  docsLoading: "Working out which documents you need…",
  docsIntro: "Tick the documents you already have. Counts cover all {total} matching schemes.",
  docsIntroAnswer: "Tick the documents you already have. Based on the {total} scheme(s) this answer is drawn from.",
  docsReady: "{n} ready to apply with the documents you have",
  docsUnknown: "{n} don't list a document we recognise: read their own pages",
  docsNeededBy: "needed by {n}",
  docsUnlocks: "getting this unlocks {n}",
  docsHave: "I have this",
  docsNone: "None of the matching schemes list a document we recognise.",
  docsError: "Could not load the document list. Please try again.",
  docsNote: "Read from each scheme's own document list. A scheme may accept an alternative; check its page.",
  schemeDocuments: "Documents to prepare",
  schemeDocumentsUnknown: "No recognised document list. Check the scheme's official page.",
  officialApply: "Official scheme / apply page",
  whyMatchedLabel: "Why this matched:",
  compareAction: "Compare",
  compareSelected: "Selected",
  comparisonTitle: "Compare schemes",
  comparisonEligibility: "Eligibility",
  comparisonBenefits: "Benefits",
  exportChecklist: "Export eligible checklist",
  exportSaved: "Export PDF",
  eligibleChecklistTitle: "Eligible Scheme Checklist",
  savedChecklistTitle: "Saved Scheme Checklist",
  checklistNotes: "Notes",
  allowPopups: "Allow pop-ups for this site to export the checklist.",
  saveScheme: "Save",
  savedScheme: "Saved",
  centralLevel: "Central",
  stateLevel: "State",
  categorySenior: "Senior Citizen",
  categoryDisability: "Person with Disability",
  categoryUnemployed: "Unemployed",
  categoryLowIncome: "BPL / Low Income",
  savedSchemes: "Saved schemes",
  conversation: "Conversation",
  sendButton: "Send",
  landingLibrary: "Source-grounded policy library",
  landingDesk: "SchemeSetu / Public Welfare Desk",
  landingDossier: "Policy dossier",
  landingFlow: "Question → record → answer",

  // 6.7 verify
  verifyButton: "Check my top {n} with AI",
  verifyWorking: "Reading eligibility text…",
  verifyIntro: "AI reads each scheme's eligibility text against your details. It can be wrong. It is not a legal decision.",
  verifyNeedProfile: "Add your age, income, state or group to use AI checking.",
  verifyFailed: "Could not check these schemes. Please try again.",
  verdictLikely: "Likely eligible",
  verdictUnclear: "Unclear",
  verdictNotEligible: "Probably not eligible",
  verdictBasedOn: "Based on",
};

const LOCAL = {
  hi: {
    schemeDocuments: "तैयार रखने वाले दस्तावेज़", schemeDocumentsUnknown: "पहचाने गए दस्तावेज़ों की सूची नहीं है। आधिकारिक पेज देखें।", officialApply: "आधिकारिक योजना / आवेदन पेज", whyMatchedLabel: "यह क्यों मिला:", compareAction: "तुलना करें", compareSelected: "चुना गया", comparisonTitle: "योजनाओं की तुलना", comparisonEligibility: "पात्रता", comparisonBenefits: "लाभ", exportChecklist: "पात्र योजनाओं की चेकलिस्ट निर्यात करें", exportSaved: "PDF निर्यात करें", eligibleChecklistTitle: "पात्र योजनाओं की चेकलिस्ट", savedChecklistTitle: "सहेजी गई योजनाओं की चेकलिस्ट", checklistNotes: "टिप्पणियाँ", allowPopups: "चेकलिस्ट निर्यात करने के लिए इस साइट के पॉप-अप की अनुमति दें।",
  },
  ta: {
    schemeDocuments: "தயாராக வைத்திருக்க வேண்டிய ஆவணங்கள்", schemeDocumentsUnknown: "அங்கீகரிக்கப்பட்ட ஆவணப் பட்டியல் இல்லை. அதிகாரப்பூர்வப் பக்கத்தைப் பார்க்கவும்.", officialApply: "அதிகாரப்பூர்வ திட்டம் / விண்ணப்பப் பக்கம்", whyMatchedLabel: "இது ஏன் பொருந்தியது:", compareAction: "ஒப்பிடு", compareSelected: "தேர்ந்தெடுக்கப்பட்டது", comparisonTitle: "திட்டங்களை ஒப்பிடு", comparisonEligibility: "தகுதி", comparisonBenefits: "நன்மைகள்", exportChecklist: "தகுதியான திட்டப் பட்டியலை ஏற்றுமதி செய்", exportSaved: "PDF ஏற்றுமதி", eligibleChecklistTitle: "தகுதியான திட்டப் பட்டியல்", savedChecklistTitle: "சேமித்த திட்டப் பட்டியல்", checklistNotes: "குறிப்புகள்", allowPopups: "பட்டியலை ஏற்றுமதி செய்ய இந்தத் தளத்தின் பாப்-அப்களை அனுமதிக்கவும்.",
  },
  te: {
    schemeDocuments: "సిద్ధం చేసుకోవాల్సిన పత్రాలు", schemeDocumentsUnknown: "గుర్తించిన పత్రాల జాబితా లేదు. అధికారిక పేజీని చూడండి.", officialApply: "అధికారిక పథకం / దరఖాస్తు పేజీ", whyMatchedLabel: "ఇది ఎందుకు సరిపోయింది:", compareAction: "పోల్చండి", compareSelected: "ఎంచుకున్నారు", comparisonTitle: "పథకాలను పోల్చండి", comparisonEligibility: "అర్హత", comparisonBenefits: "ప్రయోజనాలు", exportChecklist: "అర్హమైన పథకాల జాబితాను ఎగుమతి చేయండి", exportSaved: "PDF ఎగుమతి", eligibleChecklistTitle: "అర్హమైన పథకాల జాబితా", savedChecklistTitle: "సేవ్ చేసిన పథకాల జాబితా", checklistNotes: "గమనికలు", allowPopups: "జాబితాను ఎగుమతి చేయడానికి ఈ సైట్ పాప్-అప్‌లను అనుమతించండి.",
  },
  kn: {
    schemeDocuments: "ಸಿದ್ಧಪಡಿಸಬೇಕಾದ ದಾಖಲೆಗಳು", schemeDocumentsUnknown: "ಗುರುತಿಸಲಾದ ದಾಖಲೆಗಳ ಪಟ್ಟಿ ಇಲ್ಲ. ಅಧಿಕೃತ ಪುಟವನ್ನು ನೋಡಿ.", officialApply: "ಅಧಿಕೃತ ಯೋಜನೆ / ಅರ್ಜಿ ಪುಟ", whyMatchedLabel: "ಇದು ಏಕೆ ಹೊಂದಿಕೆಯಾಯಿತು:", compareAction: "ಹೋಲಿಸಿ", compareSelected: "ಆಯ್ಕೆಮಾಡಲಾಗಿದೆ", comparisonTitle: "ಯೋಜನೆಗಳನ್ನು ಹೋಲಿಸಿ", comparisonEligibility: "ಅರ್ಹತೆ", comparisonBenefits: "ಪ್ರಯೋಜನಗಳು", exportChecklist: "ಅರ್ಹ ಯೋಜನೆಗಳ ಪಟ್ಟಿಯನ್ನು ರಫ್ತುಮಾಡಿ", exportSaved: "PDF ರಫ್ತುಮಾಡಿ", eligibleChecklistTitle: "ಅರ್ಹ ಯೋಜನೆಗಳ ಪಟ್ಟಿ", savedChecklistTitle: "ಉಳಿಸಿದ ಯೋಜನೆಗಳ ಪಟ್ಟಿ", checklistNotes: "ಟಿಪ್ಪಣಿಗಳು", allowPopups: "ಪಟ್ಟಿಯನ್ನು ರಫ್ತು ಮಾಡಲು ಈ ಸೈಟ್‌ನ ಪಾಪ್-ಅಪ್‌ಗಳನ್ನು ಅನುಮತಿಸಿ.",
  },
  ml: {
    schemeDocuments: "തയ്യാറാക്കേണ്ട രേഖകൾ", schemeDocumentsUnknown: "തിരിച്ചറിഞ്ഞ രേഖകളുടെ പട്ടികയില്ല. ഔദ്യോഗിക പേജ് പരിശോധിക്കുക.", officialApply: "ഔദ്യോഗിക പദ്ധതി / അപേക്ഷാ പേജ്", whyMatchedLabel: "ഇത് പൊരുത്തപ്പെട്ടത് എന്തുകൊണ്ട്:", compareAction: "താരതമ്യം ചെയ്യുക", compareSelected: "തിരഞ്ഞെടുത്തു", comparisonTitle: "പദ്ധതികൾ താരതമ്യം ചെയ്യുക", comparisonEligibility: "യോഗ്യത", comparisonBenefits: "ആനുകൂല്യങ്ങൾ", exportChecklist: "യോഗ്യമായ പദ്ധതികളുടെ പട്ടിക എക്സ്പോർട്ട് ചെയ്യുക", exportSaved: "PDF എക്സ്പോർട്ട്", eligibleChecklistTitle: "യോഗ്യമായ പദ്ധതികളുടെ പട്ടിക", savedChecklistTitle: "സേവ് ചെയ്ത പദ്ധതികളുടെ പട്ടിക", checklistNotes: "കുറിപ്പുകൾ", allowPopups: "പട്ടിക എക്സ്പോർട്ട് ചെയ്യാൻ ഈ സൈറ്റിന്റെ പോപ്പ്-അപ്പുകൾ അനുവദിക്കുക.",
  },
  mr: {
    schemeDocuments: "तयार ठेवायची कागदपत्रे", schemeDocumentsUnknown: "ओळखता येणारी कागदपत्रांची यादी नाही. अधिकृत पृष्ठ पहा.", officialApply: "अधिकृत योजना / अर्ज पृष्ठ", whyMatchedLabel: "हे का जुळले:", compareAction: "तुलना करा", compareSelected: "निवडले", comparisonTitle: "योजनांची तुलना", comparisonEligibility: "पात्रता", comparisonBenefits: "लाभ", exportChecklist: "पात्र योजनांची यादी निर्यात करा", exportSaved: "PDF निर्यात करा", eligibleChecklistTitle: "पात्र योजनांची यादी", savedChecklistTitle: "जतन केलेल्या योजनांची यादी", checklistNotes: "टिपा", allowPopups: "यादी निर्यात करण्यासाठी या साइटचे पॉप-अप सुरू करा.",
  },
  bn: {
    schemeDocuments: "প্রস্তুত রাখার নথি", schemeDocumentsUnknown: "চেনা নথির তালিকা নেই। সরকারি পৃষ্ঠাটি দেখুন।", officialApply: "সরকারি প্রকল্প / আবেদনের পৃষ্ঠা", whyMatchedLabel: "এটি কেন মিলেছে:", compareAction: "তুলনা করুন", compareSelected: "নির্বাচিত", comparisonTitle: "প্রকল্প তুলনা করুন", comparisonEligibility: "যোগ্যতা", comparisonBenefits: "সুবিধা", exportChecklist: "যোগ্য প্রকল্পের তালিকা এক্সপোর্ট করুন", exportSaved: "PDF এক্সপোর্ট", eligibleChecklistTitle: "যোগ্য প্রকল্পের তালিকা", savedChecklistTitle: "সংরক্ষিত প্রকল্পের তালিকা", checklistNotes: "মন্তব্য", allowPopups: "তালিকা এক্সপোর্ট করতে এই সাইটের পপ-আপ অনুমতি দিন।",
  },
  gu: {
    schemeDocuments: "તૈયાર રાખવાના દસ્તાવેજો", schemeDocumentsUnknown: "ઓળખી શકાય તેવી દસ્તાવેજ યાદી નથી. સત્તાવાર પેજ જુઓ.", officialApply: "સત્તાવાર યોજના / અરજી પેજ", whyMatchedLabel: "આ શા માટે મેળ ખાય છે:", compareAction: "સરખાવો", compareSelected: "પસંદ કરેલ", comparisonTitle: "યોજનાઓની સરખામણી", comparisonEligibility: "પાત્રતા", comparisonBenefits: "લાભ", exportChecklist: "પાત્ર યોજનાઓની યાદી નિકાસ કરો", exportSaved: "PDF નિકાસ કરો", eligibleChecklistTitle: "પાત્ર યોજનાઓની યાદી", savedChecklistTitle: "સાચવેલી યોજનાઓની યાદી", checklistNotes: "નોંધો", allowPopups: "યાદી નિકાસ કરવા આ સાઇટના પોપ-અપની મંજૂરી આપો.",
  },
  pa: {
    schemeDocuments: "ਤਿਆਰ ਰੱਖਣ ਵਾਲੇ ਦਸਤਾਵੇਜ਼", schemeDocumentsUnknown: "ਪਛਾਣੇ ਦਸਤਾਵੇਜ਼ਾਂ ਦੀ ਸੂਚੀ ਨਹੀਂ। ਅਧਿਕਾਰਤ ਪੰਨਾ ਵੇਖੋ।", officialApply: "ਅਧਿਕਾਰਤ ਸਕੀਮ / ਅਰਜ਼ੀ ਪੰਨਾ", whyMatchedLabel: "ਇਹ ਕਿਉਂ ਮਿਲਿਆ:", compareAction: "ਤੁਲਨਾ ਕਰੋ", compareSelected: "ਚੁਣਿਆ", comparisonTitle: "ਸਕੀਮਾਂ ਦੀ ਤੁਲਨਾ", comparisonEligibility: "ਯੋਗਤਾ", comparisonBenefits: "ਲਾਭ", exportChecklist: "ਯੋਗ ਸਕੀਮਾਂ ਦੀ ਸੂਚੀ ਐਕਸਪੋਰਟ ਕਰੋ", exportSaved: "PDF ਐਕਸਪੋਰਟ ਕਰੋ", eligibleChecklistTitle: "ਯੋਗ ਸਕੀਮਾਂ ਦੀ ਸੂਚੀ", savedChecklistTitle: "ਸੰਭਾਲੀਆਂ ਸਕੀਮਾਂ ਦੀ ਸੂਚੀ", checklistNotes: "ਨੋਟਸ", allowPopups: "ਸੂਚੀ ਐਕਸਪੋਰਟ ਕਰਨ ਲਈ ਇਸ ਸਾਈਟ ਦੇ ਪੌਪ-ਅੱਪ ਮਨਜ਼ੂਰ ਕਰੋ।",
  },
};

Object.assign(LOCAL.hi, { saveScheme: "सहेजें", savedScheme: "सहेजा गया", centralLevel: "केंद्रीय", stateLevel: "राज्य", categorySenior: "वरिष्ठ नागरिक", categoryDisability: "दिव्यांग व्यक्ति", categoryUnemployed: "बेरोज़गार", categoryLowIncome: "बीपीएल / कम आय" });
Object.assign(LOCAL.ta, { saveScheme: "சேமி", savedScheme: "சேமிக்கப்பட்டது", centralLevel: "மத்திய", stateLevel: "மாநில", categorySenior: "மூத்த குடிமகன்", categoryDisability: "மாற்றுத்திறனாளி", categoryUnemployed: "வேலையில்லாதவர்", categoryLowIncome: "வறுமைக் கோட்டுக்குக் கீழ் / குறைந்த வருமானம்" });
Object.assign(LOCAL.te, { saveScheme: "సేవ్ చేయండి", savedScheme: "సేవ్ చేయబడింది", centralLevel: "కేంద్ర", stateLevel: "రాష్ట్ర", categorySenior: "వృద్ధ పౌరుడు", categoryDisability: "వైకల్యం ఉన్న వ్యక్తి", categoryUnemployed: "నిరుద్యోగి", categoryLowIncome: "BPL / తక్కువ ఆదాయం" });
Object.assign(LOCAL.kn, { saveScheme: "ಉಳಿಸಿ", savedScheme: "ಉಳಿಸಲಾಗಿದೆ", centralLevel: "ಕೇಂದ್ರ", stateLevel: "ರಾಜ್ಯ", categorySenior: "ಹಿರಿಯ ನಾಗರಿಕ", categoryDisability: "ವಿಕಲಚೇತನ ವ್ಯಕ್ತಿ", categoryUnemployed: "ನಿರುದ್ಯೋಗಿ", categoryLowIncome: "BPL / ಕಡಿಮೆ ಆದಾಯ" });
Object.assign(LOCAL.ml, { saveScheme: "സേവ് ചെയ്യുക", savedScheme: "സേവ് ചെയ്തു", centralLevel: "കേന്ദ്രം", stateLevel: "സംസ്ഥാനം", categorySenior: "മുതിർന്ന പൗരൻ", categoryDisability: "വൈകല്യമുള്ള വ്യക്തി", categoryUnemployed: "തൊഴിലില്ലാത്തവർ", categoryLowIncome: "BPL / കുറഞ്ഞ വരുമാനം" });
Object.assign(LOCAL.mr, { saveScheme: "जतन करा", savedScheme: "जतन केले", centralLevel: "केंद्र", stateLevel: "राज्य", categorySenior: "ज्येष्ठ नागरिक", categoryDisability: "दिव्यांग व्यक्ती", categoryUnemployed: "बेरोजगार", categoryLowIncome: "बीपीएल / कमी उत्पन्न" });
Object.assign(LOCAL.bn, { saveScheme: "সংরক্ষণ করুন", savedScheme: "সংরক্ষিত", centralLevel: "কেন্দ্রীয়", stateLevel: "রাজ্য", categorySenior: "প্রবীণ নাগরিক", categoryDisability: "প্রতিবন্ধী ব্যক্তি", categoryUnemployed: "বেকার", categoryLowIncome: "BPL / নিম্ন আয়" });
Object.assign(LOCAL.gu, { saveScheme: "સાચવો", savedScheme: "સાચવ્યું", centralLevel: "કેન્દ્રીય", stateLevel: "રાજ્ય", categorySenior: "વરિષ્ઠ નાગરિક", categoryDisability: "દિવ્યાંગ વ્યક્તિ", categoryUnemployed: "બેરોજગાર", categoryLowIncome: "BPL / ઓછી આવક" });
Object.assign(LOCAL.pa, { saveScheme: "ਸੰਭਾਲੋ", savedScheme: "ਸੰਭਾਲਿਆ", centralLevel: "ਕੇਂਦਰੀ", stateLevel: "ਰਾਜ", categorySenior: "ਬਜ਼ੁਰਗ ਨਾਗਰਿਕ", categoryDisability: "ਅਪੰਗਤਾ ਵਾਲਾ ਵਿਅਕਤੀ", categoryUnemployed: "ਬੇਰੁਜ਼ਗਾਰ", categoryLowIncome: "BPL / ਘੱਟ ਆਮਦਨ" });
Object.assign(LOCAL.hi, { savedSchemes: "सहेजी गई योजनाएँ", conversation: "बातचीत", sendButton: "भेजें", landingLibrary: "स्रोतों पर आधारित योजना जानकारी", landingDesk: "SchemeSetu / जनकल्याण डेस्क", landingDossier: "योजना विवरण", landingFlow: "प्रश्न → रिकॉर्ड → उत्तर" });
Object.assign(LOCAL.ta, { savedSchemes: "சேமித்த திட்டங்கள்", conversation: "உரையாடல்", sendButton: "அனுப்பு", landingLibrary: "ஆதாரங்களுடன் கூடிய திட்டத் தகவல்", landingDesk: "SchemeSetu / பொது நல மையம்", landingDossier: "திட்ட விவரம்", landingFlow: "கேள்வி → பதிவு → பதில்" });
Object.assign(LOCAL.te, { savedSchemes: "సేవ్ చేసిన పథకాలు", conversation: "సంభాషణ", sendButton: "పంపండి", landingLibrary: "ఆధారాలతో కూడిన పథకాల సమాచారం", landingDesk: "SchemeSetu / ప్రజా సంక్షేమ కేంద్రం", landingDossier: "పథకం వివరాలు", landingFlow: "ప్రశ్న → రికార్డు → సమాధానం" });
Object.assign(LOCAL.kn, { savedSchemes: "ಉಳಿಸಿದ ಯೋಜನೆಗಳು", conversation: "ಸಂಭಾಷಣೆ", sendButton: "ಕಳುಹಿಸಿ", landingLibrary: "ಮೂಲಾಧಾರಿತ ಯೋಜನೆ ಮಾಹಿತಿ", landingDesk: "SchemeSetu / ಸಾರ್ವಜನಿಕ ಕಲ್ಯಾಣ ಕೇಂದ್ರ", landingDossier: "ಯೋಜನೆಯ ವಿವರ", landingFlow: "ಪ್ರಶ್ನೆ → ದಾಖಲೆ → ಉತ್ತರ" });
Object.assign(LOCAL.ml, { savedSchemes: "സേവ് ചെയ്ത പദ്ധതികൾ", conversation: "സംഭാഷണം", sendButton: "അയയ്ക്കുക", landingLibrary: "ആധാരമുള്ള പദ്ധതി വിവരങ്ങൾ", landingDesk: "SchemeSetu / പൊതുക്ഷേമ കേന്ദ്രം", landingDossier: "പദ്ധതി വിവരങ്ങൾ", landingFlow: "ചോദ്യം → രേഖ → ഉത്തരം" });
Object.assign(LOCAL.mr, { savedSchemes: "जतन केलेल्या योजना", conversation: "संभाषण", sendButton: "पाठवा", landingLibrary: "स्रोताधारित योजना माहिती", landingDesk: "SchemeSetu / सार्वजनिक कल्याण केंद्र", landingDossier: "योजना तपशील", landingFlow: "प्रश्न → नोंद → उत्तर" });
Object.assign(LOCAL.bn, { savedSchemes: "সংরক্ষিত প্রকল্প", conversation: "কথোপকথন", sendButton: "পাঠান", landingLibrary: "সূত্র-ভিত্তিক প্রকল্পের তথ্য", landingDesk: "SchemeSetu / জনকল্যাণ কেন্দ্র", landingDossier: "প্রকল্পের বিবরণ", landingFlow: "প্রশ্ন → নথি → উত্তর" });
Object.assign(LOCAL.gu, { savedSchemes: "સાચવેલી યોજનાઓ", conversation: "વાતચીત", sendButton: "મોકલો", landingLibrary: "સ્ત્રોત આધારિત યોજના માહિતી", landingDesk: "SchemeSetu / જાહેર કલ્યાણ કેન્દ્ર", landingDossier: "યોજના વિગતો", landingFlow: "પ્રશ્ન → રેકોર્ડ → જવાબ" });
Object.assign(LOCAL.pa, { savedSchemes: "ਸੰਭਾਲੀਆਂ ਸਕੀਮਾਂ", conversation: "ਗੱਲਬਾਤ", sendButton: "ਭੇਜੋ", landingLibrary: "ਸਰੋਤਾਂ 'ਤੇ ਆਧਾਰਿਤ ਸਕੀਮ ਜਾਣਕਾਰੀ", landingDesk: "SchemeSetu / ਜਨ-ਭਲਾਈ ਕੇਂਦਰ", landingDossier: "ਸਕੀਮ ਵੇਰਵਾ", landingFlow: "ਸਵਾਲ → ਰਿਕਾਰਡ → ਜਵਾਬ" });

function fill(text, params) {
  return text.replace(/\{(\w+)\}/g, (_, k) => (params && params[k] !== undefined ? params[k] : `{${k}}`));
}

export function pt(t, key, params) {
  const translated = t(key, params);
  if (translated && translated !== key) return translated;
  const localized = LOCAL[t.language]?.[key];
  if (localized) return fill(localized, params);
  return fill(EN[key] ?? key, params);
}
