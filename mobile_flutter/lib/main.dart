import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'api_service.dart';

void main() {
  runApp(const TopoMobileApp());
}

class TopoMobileApp extends StatelessWidget {
  const TopoMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Personalizados da Rô',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFE8736A)),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _picker = ImagePicker();
  final _apiKeyController = TextEditingController();

  XFile? _selectedImage;
  bool _isLoading = false;
  String? _description;
  Uint8List? _colorImage;
  Uint8List? _maskImage;
  String? _errorMessage;

  Future<void> _pickImage() async {
    final image = await _picker.pickImage(source: ImageSource.gallery);
    if (image == null) return;
    setState(() {
      _selectedImage = image;
      _description = null;
      _colorImage = null;
      _maskImage = null;
      _errorMessage = null;
    });
  }

  Future<void> _processImage() async {
    if (_selectedImage == null) {
      setState(() => _errorMessage = 'Selecione uma imagem primeiro.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await ApiService.processImage(
        imagePath: _selectedImage!.path,
        apiKey: _apiKeyController.text.trim(),
      );

      setState(() {
        _description = response.description;
        _colorImage = base64Decode(response.imageColorBase64);
        _maskImage = base64Decode(response.maskImageBase64);
      });
    } catch (error) {
      setState(() {
        _errorMessage = error.toString();
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _apiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Personalizados da Rô'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'API Key Gemini',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _apiKeyController,
                obscureText: true,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  hintText: 'Cole sua API Key aqui',
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                icon: const Icon(Icons.photo_library),
                label: const Text('Selecionar imagem'),
                onPressed: _pickImage,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
              if (_selectedImage != null) ...[
                const SizedBox(height: 16),
                Text('Escolhido: ${_selectedImage!.name}'),
                const SizedBox(height: 16),
                Image.file(
                  File(_selectedImage!.path),
                  fit: BoxFit.contain,
                  height: 220,
                ),
              ],
              const SizedBox(height: 16),
              ElevatedButton.icon(
                icon: const Icon(Icons.play_arrow),
                label: const Text('Processar no servidor'),
                onPressed: _isLoading ? null : _processImage,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
              const SizedBox(height: 16),
              if (_isLoading) const Center(child: CircularProgressIndicator()),
              if (_errorMessage != null) ...[
                const SizedBox(height: 16),
                Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
              ],
              if (_description != null) ...[
                const SizedBox(height: 16),
                const Text('Descrição recebida:', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(_description!),
              ],
              if (_colorImage != null) ...[
                const SizedBox(height: 16),
                const Text('Folha Colorida', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Image.memory(_colorImage!, fit: BoxFit.contain),
              ],
              if (_maskImage != null) ...[
                const SizedBox(height: 16),
                const Text('Máscara de Corte', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Image.memory(_maskImage!, fit: BoxFit.contain),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
