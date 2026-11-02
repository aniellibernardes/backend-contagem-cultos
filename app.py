from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)  # Permite que a interface no GitHub Pages se comunique com este servidor na nuvem

# Inicializa a conexão com o Firebase (banco 'contagem')
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client(database_id="contagem")

@app.route('/salvar-culto', methods=['POST'])
def salvar_culto():
    try:
        dados = request.json
        
        data_str = dados.get('data')
        dt_obj = datetime.strptime(data_str, "%Y-%m-%d")
        
        # Extrai os dados enviados pelo site
        aud = dados.get('auditorio', {})
        pk = dados.get('playkids', {})
        cls = dados.get('class', {})
        
        # Processamento e Somatória feita pelo Python
        sub_aud = int(aud.get('adultos', 0)) + int(aud.get('criancas', 0)) + int(aud.get('adolescentes', 0))
        sub_pk = int(pk.get('adultos', 0)) + int(pk.get('criancas', 0))
        sub_class = int(cls.get('adultos', 0)) + int(cls.get('adolescentes', 0))
        
        total_geral = sub_aud + sub_pk + sub_class
        
        # Monta o objeto estruturado para o Firebase
        registro = {
            "data": data_str,
            "ano": dt_obj.year,
            "mes": dt_obj.month,
            "semana": int(dt_obj.strftime('%U')),
            "culto": dados.get('culto'),
            "responsavel": dados.get('responsavel'),
            "auditorio": {
                "adultos": int(aud.get('adultos', 0)),
                "criancas": int(aud.get('criancas', 0)),
                "adolescentes": int(aud.get('adolescentes', 0)),
                "subtotal": sub_aud
            },
            "playkids": {
                "adultos": int(pk.get('adultos', 0)),
                "criancas": int(pk.get('criancas', 0)),
                "subtotal": sub_pk
            },
            "class": {
                "adultos": int(cls.get('adultos', 0)),
                "adolescentes": int(cls.get('adolescentes', 0)),
                "subtotal": sub_class
            },
            "total_geral": total_geral,
            "criado_em": firestore.SERVER_TIMESTAMP
        }

        # Grava no banco de dados nomeado como 'contagem'
        db.collection("cultos").add(registro)
        
        return jsonify({
            "status": "sucesso", 
            "mensagem": "Culto processado e gravado no Firebase com sucesso!",
            "total_geral": total_geral
        }), 200

    except Exception as e:
        return jsonify({"status": "erro", "detalhes": str(e)}), 500

@app.route('/consultar-cultos', methods=['GET'])
def consultar_cultos():
    try:
        tipo = request.args.get('tipo', 'diario')
        cultos_ref = db.collection("cultos").stream()
        
        lista_cultos = []
        for doc in cultos_ref:
            lista_cultos.append(doc.to_dict())

        # Exemplo de retorno consolidado para os relatórios
        if not lista_cultos:
            return jsonify([]), 200

        # Retorno simplificado para preencher os relatórios na interface
        resultados = [{
            "titulo": "Dados Consolidados Gerais",
            "quantidade_cultos": len(lista_cultos),
            "soma_total": sum(c.get('total_geral', 0) for c in lista_cultos),
            "media": sum(c.get('total_geral', 0) for c in lista_cultos) / len(lista_cultos)
        }]

        return jsonify(resultados), 200

    except Exception as e:
        return jsonify({"status": "erro", "detalhes": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)