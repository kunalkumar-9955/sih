/// RouteIQ — Mobile Centralized Localization Service
/// Provides instant in-memory translations across all 6 Northeast regional languages:
/// English (en), Hindi (hi), Assamese (as), Bengali (bn), Manipuri (mni), Khasi (kha).

import 'package:shared_preferences/shared_preferences.dart';

class LocalizationService {
  static const String prefKey = 'preferred_language';
  static String currentLanguage = 'en';

  static final Map<String, Map<String, String>> _localizedValues = {
    'en': {
      'app_name': 'RouteIQ',
      'driver_console': 'Driver Console',
      'welcome': 'Welcome',
      'active_trip': 'Current Active Trip',
      'continue_trip': 'Continue Navigation',
      'view_route': 'View Full Route',
      'shipment': 'Active Shipment Manifest',
      'alerts': 'Route Hazard Alerts',
      'sos': 'Emergency SOS',
      'offline_mode': 'Offline Mode Active',
      'synced': 'Up to Date',
      'origin': 'Origin Terminal',
      'destination': 'Destination Hub',
      'remaining_dist': 'Remaining Distance',
      'eta': 'Estimated Arrival',
      'safe': 'Safe (Low Hazard)',
      'high_risk': 'High Hazard Detected',
      'accept_detour': 'Accept Safer Detour',
      'keep_route': 'Maintain Current Route',
    },
    'hi': {
      'app_name': 'RouteIQ',
      'driver_console': 'ड्राइवर कंसोल',
      'welcome': 'स्वागत है',
      'active_trip': 'वर्तमान असाइन की गई यात्रा',
      'continue_trip': 'नेविगेशन जारी रखें',
      'view_route': 'पूरा रूट देखें',
      'shipment': 'सक्रिय माल घोषणा (मेनिफेस्ट)',
      'alerts': 'मार्ग खतरा चेतावनी',
      'sos': 'आपातकालीन एसओएस',
      'offline_mode': 'ऑफलाइन मोड सक्रिय',
      'synced': 'अप टू डेट',
      'origin': 'शुरुआती टर्मिनल',
      'destination': 'गंतव्य हब',
      'remaining_dist': 'शेष दूरी',
      'eta': 'अनुमानित आगमन समय',
      'safe': 'सुरक्षित (कम जोखिम)',
      'high_risk': 'उच्च जोखिम चेतावनी',
      'accept_detour': 'सुरक्षित डायवर्जन स्वीकार करें',
      'keep_route': 'वर्तमान रूट पर रहें',
    },
    'as': {
      'app_name': 'RouteIQ',
      'driver_console': 'চালকলৈ কঞ্চোল',
      'welcome': 'স্বাগতম',
      'active_trip': 'বৰ্তমান চলিত যাত্ৰা',
      'continue_trip': 'যাত্ৰা আগবঢ়াওক',
      'view_route': 'সম্পূৰ্ণ পথ চাওক',
      'shipment': 'সক্ৰিয় চালানৰ নথি',
      'alerts': 'পথৰ বিপদ সংকেত',
      'sos': 'জৰুৰীকালীন এছঅ’এছ (SOS)',
      'offline_mode': 'অফলাইন মড সক্ৰিয়',
      'synced': 'সম্পূৰ্ণ আপডেট',
      'origin': 'আৰম্ভণি স্থান',
      'destination': 'গন্তব্য হাব',
      'remaining_dist': 'বাকী থকা দূৰত্ব',
      'eta': 'সম্ভাব্য সময়',
      'safe': 'সুৰক্ষিত (কম বিপদ)',
      'high_risk': 'অতি বিপদসংকুল পথ',
      'accept_detour': 'সুৰক্ষিত বিকল্প গ্ৰহণ কৰক',
      'keep_route': 'পুৰণি পথতে থাকক',
    },
    'bn': {
      'app_name': 'RouteIQ',
      'driver_console': 'ড্রাইভার ড্যাশবোর্ড',
      'welcome': 'স্বাগতম',
      'active_trip': 'বর্তমানে বরাদ্দকৃত ট্রিপ',
      'continue_trip': 'নেভিগেশন চালিয়ে যান',
      'view_route': 'সম্পূর্ণ রুট দেখুন',
      'shipment': 'সক্রিয় চালান নথি',
      'alerts': 'পথের সতর্কতা',
      'sos': 'জরুরী এসওএস (SOS)',
      'offline_mode': 'অফলাইন মোড সক্রিয়',
      'synced': 'আপ টু ডেট',
      'origin': 'যাত্রার শুরু',
      'destination': 'গন্তব্য হাব',
      'remaining_dist': 'অবশিষ্ট দূরত্ব',
      'eta': 'সম্ভাব্য সময়',
      'safe': 'নিরাপদ (কম ঝুঁকি)',
      'high_risk': 'উচ্চ ঝুঁকি সনাক্ত',
      'accept_detour': 'নিরাপদ বিকল্প গ্রহণ করুন',
      'keep_route': 'বর্তমান পথ বজায় রাখুন',
    },
    'mni': {
      'app_name': 'RouteIQ',
      'driver_console': 'দ্রাইভর দেশবোর্দ',
      'welcome': 'তরাম্না ওকচরি',
      'active_trip': 'হৌজিক লৈরিবা খোঙচৎ',
      'continue_trip': 'লম্বী মখা চত্থবা',
      'view_route': 'লম্বী পুম্নমক য়েংবা',
      'shipment': 'পোৎলমগী চে',
      'alerts': 'লম্বীগী চেকশিনৱা',
      'sos': 'অকনবা এসওএস',
      'offline_mode': 'ওফলাইন মোদ চৎনরি',
      'synced': 'অপ তু দেত',
      'origin': 'হৌরকফম',
      'destination': 'য়ৌগদবা মফম',
      'remaining_dist': 'লেমহৌরিবা লম্বী',
      'eta': 'য়ৌগদবা মতম',
      'safe': 'অশোয়বা লৈতবা',
      'high_risk': 'খুদোংথীবা লৈরে',
      'accept_detour': 'সেফ লম্বীদা চৎপা য়ারবা',
      'keep_route': 'হৌজিক্কী লম্বীদা চৎপা',
    },
    'kha': {
      'app_name': 'RouteIQ',
      'driver_console': 'Ka Dashboard U Nongniah',
      'welcome': 'Khublei',
      'active_trip': 'Ka Jingiaid Lynti ba la Ai',
      'continue_trip': 'Bteng ia ka Lynti',
      'view_route': 'Peit Lut ia ka Lynti',
      'shipment': 'Ka Dokument ba Kit Mar',
      'alerts': 'Ki Jingma ha Lynti',
      'sos': 'SOS Jingkyrpad',
      'offline_mode': 'Offline Mode Trei Kam',
      'synced': 'Lah Dep Baroh',
      'origin': 'Nangne Sdang',
      'destination': 'Sha Kaba Thmu',
      'remaining_dist': 'Jngai ban Poi',
      'eta': 'Por ban Poi',
      'safe': 'Shngiain (Khlm Jingma)',
      'high_risk': 'Don Jingma ba Khraw',
      'accept_detour': 'Pdiang Lynti Thymmai',
      'keep_route': 'Iaipynneh Lynti Mynshuwa',
    },
  };

  static Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    currentLanguage = prefs.getString(prefKey) ?? 'en';
  }

  static Future<void> setLanguage(String code) async {
    if (_localizedValues.containsKey(code)) {
      currentLanguage = code;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(prefKey, code);
    }
  }

  static String tr(String key, {String? fallback}) {
    final dict = _localizedValues[currentLanguage] ?? _localizedValues['en']!;
    return dict[key] ?? fallback ?? key;
  }
}
