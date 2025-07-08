// This is a basic Flutter widget test for the SMS Reader App.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sms_reader_app/main.dart';

void main() {
  testWidgets('SMS Reader App smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const SmsReaderApp());

    // Verify that the app loads with the correct title
    expect(find.text('SMS Reader & Analyzer'), findsOneWidget);
    
    // Verify that key UI elements are present
    expect(find.text('Request Permission'), findsOneWidget);
    expect(find.text('Load SMS'), findsOneWidget);
    expect(find.text('Send to Analyzer'), findsOneWidget);
    
    // Verify status card is present
    expect(find.text('Status'), findsOneWidget);
    
    // Verify initial message is shown
    expect(find.text('No SMS messages loaded'), findsOneWidget);
  });

  testWidgets('Settings button opens URL dialog', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const SmsReaderApp());

    // Find and tap the settings button
    await tester.tap(find.byIcon(Icons.settings));
    await tester.pumpAndSettle();

    // Verify that the dialog opens
    expect(find.text('Set Server URL'), findsOneWidget);
    expect(find.text('Server URL'), findsOneWidget);
  });
}
