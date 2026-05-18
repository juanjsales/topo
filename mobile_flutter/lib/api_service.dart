import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

class ProcessResponse {
  final String description;
  final String imageColorBase64;
  final String maskImageBase64;

  ProcessResponse({
    required this.description,
    required this.imageColorBase64,
    required this.maskImageBase64,
  });

  factory ProcessResponse.fromJson(Map<String, dynamic> json) {
    return ProcessResponse(
      description: json['description'] as String,
      imageColorBase64: json['image_color_base64'] as String,
      maskImageBase64: json['mask_image_base64'] as String,
    );
  }
}

class ApiService {
  // Exemplo se fosse usar Vercel ou Render
  static const String backendUrl = 'https://topo-api.onrender.com';

  static Future<ProcessResponse> processImage({
    required String imagePath,
    required String apiKey,
  }) async {
    final uri = Uri.parse('$backendUrl/process');
    final request = http.MultipartRequest('POST', uri);
    if (apiKey.isNotEmpty) {
      request.fields['api_key'] = apiKey;
    }
    request.files.add(await http.MultipartFile.fromPath('image', imagePath));

    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 200) {
        // Tenta decodificar uma mensagem de erro mais detalhada do backend
        try {
          final errorBody = jsonDecode(response.body);
          final detail = errorBody['detail'] ?? response.body;
          throw Exception('Falha no servidor (${response.statusCode}): $detail');
        } catch (_) {
          throw Exception('Falha ao processar a imagem: ${response.statusCode}');
        }
      }

      final jsonResponse = jsonDecode(response.body) as Map<String, dynamic>;
      return ProcessResponse.fromJson(jsonResponse);
    } on SocketException {
      throw Exception(
          'Erro de conexão: Não foi possível encontrar o servidor. Verifique sua internet ou tente novamente em um minuto, pois o servidor pode estar "acordando".');
    } catch (e) {
      throw Exception('Ocorreu um erro inesperado: $e');
    }
  }
}
