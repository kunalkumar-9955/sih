import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../theme/app_theme.dart';
import 'login_screen.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  Future<void> _logout(BuildContext context) async {
    const storage = FlutterSecureStorage();
    await storage.deleteAll();
    if (context.mounted) {
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      appBar: AppBar(title: const Text("Driver Profile & Cache")),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 72,
                height: 72,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [AppTheme.accentCyan, Color(0xFF2563EB)],
                  ),
                ),
                child: const Icon(Icons.person, size: 40, color: Colors.white),
              ),
            ),
            const SizedBox(height: 14),
            const Text(
              "Tenzing Norgay",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            const Text(
              "Assam Heavy Vehicle License • AS-01-2023-9988",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 28),

            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.bgSurface,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("Offline Vector Tiles", style: TextStyle(fontSize: 13)),
                      Text("142 MB Cached", style: TextStyle(color: AppTheme.accentEmerald, fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                  Divider(height: 24, color: Color(0x15FFFFFF)),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("Assam-Meghalaya Graph", style: TextStyle(fontSize: 13)),
                      Text("26 Nodes • 38 Edges", style: TextStyle(color: AppTheme.accentCyan, fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                  Divider(height: 24, color: Color(0x15FFFFFF)),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("Dead-Zone Sync Buffer", style: TextStyle(fontSize: 13)),
                      Text("Zero Outbox Pending", style: TextStyle(color: AppTheme.accentEmerald, fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                ],
              ),
            ),

            const Spacer(),

            OutlinedButton.icon(
              onPressed: () => _logout(context),
              icon: const Icon(Icons.logout, color: AppTheme.accentRose),
              label: const Text("Log Out from Driver Terminal", style: TextStyle(color: AppTheme.accentRose)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppTheme.accentRose),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
