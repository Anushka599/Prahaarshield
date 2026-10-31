# v3.3 gap data (financial scope, our 6 types). Written fresh from the user's test chats and 2026 advisories; never copied.
G = []
def add(t, lang, rows, cat):
    for x in rows: G.append((x, lang, t, cat))
# --- 1. known-contact impersonation (hacked friend / relative account asks for money) -> boss_impersonation
add("boss_impersonation", "hinglish", ["Bhai mera phone kharab ho gaya, ye naya number hai. ₹15,000 abhi bhej de, kal pakka lauta dunga",
 "Yaar hospital me hu, mummy ko mat batana. ₹22,000 urgent chahiye, call mat kar network nahi hai yaha", "Didi meri UPI limit khatam ho gayi, ₹9,000 is account me bhej do jaldi please 🙏",
 "Arre call mat kar abhi meeting me hu, bas ₹12,000 bhej de 10 min me, baad me sab batata hu", "Mama ka accident hua hai, ₹30,000 turant chahiye, ghar pe kisi ko mat batana abhi",
 "Bro ye mera second number hai, purana band hai. ₹7,500 GPay kar de jaldi, shaam ko return", "Paise bhej na yaar, kitni der lagayega? Warna mera bahut nuksaan ho jayega",
 "Call nahi utha sakta, bas jaldi ₹18,000 bhej. Kisi se discuss mat karna please"], "known_contact_v33")
add("boss_impersonation", "mr", ["अगं माझा फोन बिघडला, हा नवीन नंबर आहे. ₹15,000 लगेच पाठव, उद्या परत देतो", "मी हॉस्पिटलमध्ये आहे, आईला सांगू नकोस. ₹20,000 पटकन पाठव, कॉल करू नको इथे रेंज नाही",
 "Tai mazi UPI limit sampli, ₹9,000 ya account var pathav ga patkan", "Call karu nakos ata meeting madhe aahe, fakt ₹12,000 pathav 10 minitat",
 "मामाचा अपघात झाला आहे, ₹30,000 लगेच हवे आहेत, घरी कोणाला सांगू नको", "He maza navin number aahe, junya varun msg nako karu. ₹6,000 GPay kar lagech"], "known_contact_v33")
add("boss_impersonation", "hi_deva", ["भाई मेरा फोन खराब हो गया, ये नया नंबर है। ₹15,000 अभी भेज दो, कल लौटा दूँगा", "मैं अस्पताल में हूँ, मम्मी को मत बताना। ₹25,000 तुरंत चाहिए, कॉल मत करना",
 "दीदी मेरी यूपीआई लिमिट खत्म हो गई, ₹9,000 इस खाते में जल्दी भेज दो", "कॉल मत करो अभी मीटिंग में हूँ, बस ₹12,000 दस मिनट में भेज दो"], "known_contact_v33")
add("boss_impersonation", "en", ["Hey it's me, lost my phone so using this new number. Can you send ₹15,000 right now? Will return tomorrow",
 "I'm at the hospital, don't tell mom yet. Need ₹25,000 urgently, can't take calls here", "My UPI limit is over, please send ₹9,000 to this account quickly, I'll explain later",
 "Don't call, I'm in a meeting. Just transfer ₹12,000 in the next 10 mins please"], "known_contact_v33")
# genuine friend / family money asks (normal tone, no secrecy, no new number, no call blocking)
add("benign", "hinglish", ["Bhai ₹2,000 bhej de kal tak, salary aate hi lauta dunga 🙏", "Didi ₹500 GPay kar do, auto wale ko dena hai, ghar aake de dungi",
 "Mummy ₹3,000 bhej do books ke liye, bill photo bhejti hu", "Yaar ₹1,200 de de movie tickets ke, tu hi book kar raha hai na"], "known_contact_benign_v33")
add("benign", "mr", ["आई ₹2,000 पाठव ना, पुस्तकं घ्यायची आहेत, बिल पाठवते", "Dada ₹500 pathav na rickshaw sathi, ghari aalyavar deto", "Bhau ₹1,000 de re, udya salary aali ki parat karto"], "known_contact_benign_v33")
add("benign", "hi_deva", ["पापा ₹3,000 भेज दो कॉलेज फीस के लिए, रसीद भेज दूँगी", "भाई ₹1,500 भेज दे, शाम को घर आकर दे दूँगा"], "known_contact_benign_v33")
add("benign", "en", ["Can you send me ₹2,000 till Friday? Salary gets credited then, will return", "Mom please send ₹1,500 for the project kit, I'll share the bill"], "known_contact_benign_v33")
# --- 2. genuine promotions (benign) - urgency and emojis are normal in real offers
add("benign", "en", ["Festive week deal: 35% off on all design courses, enrol on our website 🎨 Ends Sunday", "Big Billion Days are live 🔥 Up to 70% off on electronics. Shop now in the app",
 "Your Swiggy One membership expires in 3 days. Renew now to keep free deliveries 🛵", "Weekend special at Cafe Coffee Day: buy 1 get 1 free on all cold coffees ☕",
 "Last 2 days of the Monsoon Sale! Extra 10% off with HDFC cards on our website", "New batch for Python course starts Monday. Early-bird fee ₹2,999 till Friday 🚀",
 "Dear member, your gym's Diwali offer: 3 months at ₹4,500. Visit the front desk", "Myntra End of Reason Sale starts tonight at 8 PM 🛍️ Add to wishlist now"], "promo_benign_v33")
add("benign", "hinglish", ["Diwali dhamaka! Saare kurtas pe 50% off, sirf is weekend 🪔 Store pe aaiye", "Aapka Jio plan kal expire ho raha hai, MyJio app se recharge karein",
 "Naya batch aa raha hai coaching me, fees pe 20% discount sirf is hafte tak 📚", "Big sale chal rahi hai bhai Amazon pe, phone sasta mil raha hai 🔥"], "promo_benign_v33")
add("benign", "mr", ["दिवाळी ऑफर! सर्व साड्यांवर 30% सूट, फक्त या रविवारपर्यंत 🪔", "Tumcha recharge udya sampnar aahe, MyJio app varun recharge kara",
 "नवीन क्लासची बॅच सोमवारपासून, या आठवड्यात फीवर 20% सूट 📚"], "promo_benign_v33")
add("benign", "hi_deva", ["दिवाली ऑफर! सभी कपड़ों पर 40% छूट, सिर्फ़ इस रविवार तक 🪔", "आपका प्लान कल खत्म हो रहा है, आधिकारिक ऐप से रिचार्ज करें"], "promo_benign_v33")
# --- 3. Devanagari 'pay a fee to withdraw' investment scams
add("investment_group", "hi_deva", ["आपके खाते में ₹2,40,000 मुनाफ़ा है, निकालने से पहले ₹36,000 टैक्स भरें", "निकासी रुकी है, ₹15,000 सर्विस फीस जमा करो तभी पैसा मिलेगा",
 "मुनाफ़ा निकालना है तो पहले 10% शुल्क भरिए, वरना खाता बंद", "VIP ग्रुप में आपका ₹85,000 बैलेंस है, निकालने के लिए ₹12,500 मार्जिन जमा करें",
 "आज ₹20,000 और लगाओ तो दोगुना मिलेगा, निकासी के लिए भी यही ज़रूरी है"], "withdraw_v33")
add("investment_group", "mr", ["तुमच्या खात्यात ₹2,40,000 नफा आहे, काढण्याआधी ₹36,000 कर भरा", "पैसे काढणे थांबले आहे, ₹15,000 सर्व्हिस फी भरा मग पैसे मिळतील",
 "नफा काढायचा असेल तर आधी 10% शुल्क भरा, नाहीतर खाते बंद", "VIP ग्रुपमध्ये तुमची ₹85,000 शिल्लक आहे, काढण्यासाठी ₹12,500 मार्जिन भरा"], "withdraw_v33")
# --- 4. WhatsApp code hijack -> kyc_bank (credential / account takeover)
add("kyc_bank", "hinglish", ["Sorry yaar galti se tujhe ek 6 digit code chala gaya, forward kar de please", "Ek code aaya hoga tere phone pe mere naam se, wo bhej de jaldi",
 "Mera WhatsApp verify nahi ho raha, tere number pe code gaya hai, bata de na"], "wa_code_v33")
add("kyc_bank", "en", ["Hey, I accidentally sent a 6-digit code to your number, can you forward it to me?", "You must have received a WhatsApp verification code by mistake, please share it",
 "Sorry, my code went to your phone. Just send me the 6 digits quickly"], "wa_code_v33")
add("kyc_bank", "mr", ["चुकून तुझ्या नंबरवर एक 6 अंकी कोड आलाय, तो मला पाठव ना", "Mazha WhatsApp verify hot nahiye, tuzya number var code aala asel to pathav"], "wa_code_v33")
add("kyc_bank", "hi_deva", ["गलती से आपके नंबर पर 6 अंकों का कोड चला गया, वो मुझे भेज दीजिए", "मेरा व्हाट्सऐप वेरिफ़ाई नहीं हो रहा, आपके फोन पर आया कोड बता दो"], "wa_code_v33")
# --- 5. family OTP / delivery (benign)
add("benign", "hinglish", ["Amazon wala aaya hai, OTP aaya hoga tere phone pe, bata de 📦", "Gas cylinder wala OTP maang raha hai, mere phone pe nahi aaya, tere pe aaya kya?",
 "Netflix ka login code aaya hoga, bata de TV pe daal rahi hu 📺", "Swiggy delivery ka OTP bhej de, main bahar hu"], "family_otp_v33")
add("benign", "mr", ["Amazon चा डिलिव्हरीवाला आलाय, OTP आला असेल तो सांग", "गॅसवाला OTP मागतोय, तुझ्या फोनवर आला का?", "Zomato cha OTP sang re, mi khali jatey"], "family_otp_v33")
add("benign", "en", ["The delivery guy is here, can you tell me the OTP that came on your phone?", "Mom's phone is off, the cylinder OTP came to you, can you share it?"], "family_otp_v33")
add("benign", "hi_deva", ["डिलीवरी वाला आया है, आपके फोन पर आया ओटीपी बता दो", "गैस वाला ओटीपी माँग रहा है, आपके फोन पर आया क्या?"], "family_otp_v33")
# --- 6. genuine 'remember me?' openers (benign) - so familiarity alone never means scam
add("benign", "hinglish", ["Arre pehchana? School wala Rohit, 10th B! Kaisa hai bhai 😄", "Yaad hai Goa trip? Photos mil gayi, group me bhejta hu 📸"], "familiar_benign_v33")
add("benign", "en", ["Hey! Remember me from the Pune hackathon? We were in the same team 😊", "Long time! Saw your post about the new job, congrats!!"], "familiar_benign_v33")
add("benign", "mr", ["अरे ओळखलं का? शाळेतला सागर, दहावी ब! कसा आहेस 😄", "Aathavta ka Lonavala trip? Photos sapadle, group var takto"], "familiar_benign_v33")
