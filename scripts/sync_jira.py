"""
sync_jira.py
Consulta o status de cada issue no JIRA e grava no Firebase Realtime Database.
Executado pelo GitHub Actions a cada 2 horas.
"""

import os
import json
import time
import urllib.request
import urllib.error
import base64

# ── Configuração ──────────────────────────────────────────────────────────────
JIRA_BASE    = 'https://jiraproducao.totvs.com.br/rest/api/2/issue'
FIREBASE_URL = 'https://catalogodvarpr-default-rtdb.firebaseio.com'

JIRA_USER = os.environ['JIRA_USER']
JIRA_PASS = os.environ['JIRA_PASS']
AUTH      = base64.b64encode(f'{JIRA_USER}:{JIRA_PASS}'.encode()).decode()

# ── Issues por épico ──────────────────────────────────────────────────────────
ISSUES_D8 = [
    'DVARPR-35',
    'DVARPR-209', 'DVARPR-25',  'DVARPR-29',  'DVARPR-32',  'DVARPR-90',
    'DVARPR-123', 'DVARPR-115', 'DVARPR-116', 'DVARPR-121', 'DVARPR-117',
    'DVARPR-118', 'DVARPR-119', 'DVARPR-120', 'DVARPR-122', 'DVARPR-124',
    'DVARPR-125', 'DVARPR-133', 'DVARPR-134', 'DVARPR-135', 'DVARPR-136',
    'DVARPR-137', 'DVARPR-138', 'DVARPR-139', 'DVARPR-393', 'DVARPR-394',
    'DVARPR-395', 'DVARPR-435', 'DVARPR-436', 'DVARPR-437',
    'DVARPR-130', 'DVARPR-457', 'DVARPR-462',
    'DVARPV-6716',
    'DVARPR-396', 'DVARPR-397', 'DVARPR-398', 'DVARPR-399', 'DVARPR-400',
    'DVARPR-401', 'DVARPR-405', 'DVARPR-406', 'DVARPR-407', 'DVARPR-408',
    'DVARPR-409', 'DVARPR-410', 'DVARPR-411', 'DVARPR-412', 'DVARPR-413',
    'DVARPR-414', 'DVARPR-415', 'DVARPR-419', 'DVARPR-420', 'DVARPR-421',
    'DVARPR-422', 'DVARPR-423', 'DVARPR-424', 'DVARPR-425', 'DVARPR-426',
    'DVARPR-427',
    'DVARPR-441', 'DVARPR-442', 'DVARPR-443', 'DVARPR-447', 'DVARPR-448',
    'DVARPR-449', 'DVARPR-452', 'DVARPR-453', 'DVARPR-454', 'DVARPR-455',
    'DVARPR-456', 'DVARPR-467', 'DVARPR-468', 'DVARPR-470', 'DVARPR-471',
    'DVARPR-473', 'DVARPR-474', 'DVARPR-478', 'DVARPR-479', 'DVARPR-480',
    'DVARPR-481', 'DVARPR-482', 'DVARPR-483', 'DVARPR-484',
]

ISSUES_D1 = [
    'DVARPR-2', 'DVARPR-378', 'DVARPR-379', 'DVARPR-380', 'DVARPR-381',
]

# ── Mapeamento de status JIRA → Dashboard ─────────────────────────────────────
# Os status do JIRA já estão em português e coincidem com os do dashboard.
# Este mapa cobre variações e garante consistência.
STATUS_MAP = {
    'concluído':              'Concluído',
    'concluido':              'Concluído',
    'done':                   'Concluído',
    'closed':                 'Concluído',
    'resolved':               'Concluído',
    'code review concluído':  'Code Review Concluído',
    'code review':            'Code Review Concluído',
    'in review':              'Code Review Concluído',
    'em teste':               'Em Teste',
    'in test':                'Em Teste',
    'testing':                'Em Teste',
    'em desenvolvimento':     'Em Desenvolvimento',
    'em andamento':           'Em Desenvolvimento'
    'in progress':            'Em Desenvolvimento',
    'in development':         'Em Desenvolvimento',
    'comprometido':           'Comprometido',
    'committed':              'Comprometido',
    'selected for development': 'Comprometido',
    'backlog':                'Backlog',
    'to do':                  'Backlog',
    'open':                   'Backlog',
    'planejado':              'Planejado',
    'planned':                'Planejado',
}

# ── Funções ───────────────────────────────────────────────────────────────────
def fetch_status(issue_id):
    """Busca o status atual de uma issue no JIRA. Retorna None em caso de erro."""
    url = f'{JIRA_BASE}/{issue_id}?fields=status'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Basic {AUTH}',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            raw = data['fields']['status']['name']
            mapped = STATUS_MAP.get(raw.lower())
            if mapped:
                return mapped
            else:
                print(f'  ⚠ Status desconhecido para {issue_id}: "{raw}" — mantendo como está')
                return raw   # retorna o valor bruto para não perder informação
    except urllib.error.HTTPError as e:
        print(f'  ✗ {issue_id}: HTTP {e.code}')
        return None
    except Exception as e:
        print(f'  ✗ {issue_id}: {e}')
        return None


def sync_epico(issue_ids, firebase_path, label):
    """Busca status de todas as issues e grava no Firebase."""
    print(f'\n── {label} ({len(issue_ids)} issues) ──')
    overrides = {}
    for issue_id in issue_ids:
        status = fetch_status(issue_id)
        if status:
            overrides[issue_id] = status
            print(f'  ✓ {issue_id}: {status}')
        time.sleep(0.3)   # evita rate limit do JIRA

    # Gravar no Firebase via REST API
    url = f'{FIREBASE_URL}/{firebase_path}.json'
    payload = json.dumps(overrides).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='PUT', headers={
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f'\n  ✅ Firebase atualizado: {firebase_path} ({len(overrides)} issues gravadas)')
    except Exception as e:
        print(f'\n  ✗ Erro ao gravar no Firebase: {e}')
        raise


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('🔄 Iniciando sincronização JIRA → Firebase...')
    sync_epico(ISSUES_D8, 'status/dvarpr8', 'DVARPR-8 — Catálogo de Produtos')
    sync_epico(ISSUES_D1, 'status/dvarpr1', 'DVARPR-1 — Consulta e Transferência')
    print('\n✅ Sincronização concluída.')
