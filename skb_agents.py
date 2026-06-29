# skb_agents.py
# SKB_STAT uchun Multi-Agent tizimi
# Ishlatish: python skb_agents.py

import anthropic
import asyncio
import json

client = anthropic.Anthropic()  # ANTHROPIC_API_KEY env dan oladi

# ─── AGENT ROLLARI ────────────────────────────────────────────────────────────

AGENTS = {
    "patients": {
        "role": "Patients app mutaxassisi",
        "context": """
Sen SKB_STAT loyihasining PATIENTS app agentisan.
Mas'uliyating: apps/patients/ — bemor qabuli, ro'yxat, ko'chirish, chiqarish.
Asosiy modellar: PatientCard, DepartmentTransfer, Department
Muhim: patient_category (railway/non_resident/other), select_related() ishlatish
"""
    },
    "services": {
        "role": "Services app mutaxassisi",
        "context": """
Sen SKB_STAT loyihasining SERVICES app agentisan.
Mas'uliyating: apps/services/ — xizmatlar, narxlar, paketlar, dorilar.
Asosiy modellar: Service, PatientService, ServiceCategory, DoctorServicePackage
Muhim: non_resident uchun 25% ustama, price_for_patient() metodi
"""
    },
    "statistic": {
        "role": "Statistika app mutaxassisi",
        "context": """
Sen SKB_STAT loyihasining STATISTIC app agentisan.
Mas'uliyating: apps/statistic/ — hisobotlar, Excel export, grafik.
Muhim: N+1 muammolardan saqlaning, aggregate() to'g'ri ishlating
Django 5.2 bug: annotate+aggregate o'rniga Sum(ExpressionWrapper()) ishlating
"""
    },
    "users": {
        "role": "Users app mutaxassisi",
        "context": """
Sen SKB_STAT loyihasining USERS app agentisan.
Mas'uliyating: apps/users/ — foydalanuvchilar, rollar, autentifikatsiya.
Rollar: admin, reception, doctor, statistician, laborant, viewer
Muhim: AUTH_USER_MODEL = 'users.CustomUser'
"""
    },
    "laboratory": {
        "role": "Laboratory app mutaxassisi",
        "context": """
Sen SKB_STAT loyihasining LABORATORY app agentisan.
Mas'uliyating: apps/laboratory/ — lab buyurtmalar, shablonlar, natijalar.
Asosiy modellar: LabTemplate, LabParameter, LabOrder, LabResult
18 ta tahlil turi, 150+ parametr
"""
    },
}

# ─── WORKER AGENT ──────────────────────────────────────────────────────────────

async def worker_agent(app_name: str, task: str) -> dict:
    """Bitta app uchun ishchi agent"""
    agent = AGENTS.get(app_name)
    if not agent:
        return {"app": app_name, "result": f"Agent topilmadi: {app_name}"}

    print(f"  🔄 [{app_name}] ishlamoqda...")

    # Sync call ni async ga o'rash
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=f"""Sen SKB_STAT loyihasining {agent['role']}san.
Django 5.2, PostgreSQL, Bootstrap 5 ishlatiladi.
O'zbekcha interfeys.

{agent['context']}

Faqat o'z app ingga tegishli kod yoz. Qisqa va aniq bo'l.""",
        messages=[{"role": "user", "content": task}]
    ))

    return {
        "app": app_name,
        "result": response.content[0].text
    }

# ─── ORCHESTRATOR (BOSH AGENT) ─────────────────────────────────────────────────

async def orchestrator(main_task: str):
    """
    Bosh agent:
    1. Vazifani tahlil qiladi
    2. Qaysi agentlar kerakligini aniqlaydi
    3. Ularni parallel ishga tushiradi
    4. Natijalarni birlashtiradi
    """
    print(f"\n{'='*60}")
    print(f"🎯 BOSH AGENT: {main_task}")
    print(f"{'='*60}\n")

    # 1. Planner — qaysi agentlar kerak?
    print("📋 Planner vazifalarni taqsimlayapti...")

    loop = asyncio.get_event_loop()
    plan_response = await loop.run_in_executor(None, lambda: client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system="""SKB_STAT loyiha orchestratorisan.
Vazifani tahlil qil va qaysi app agentlari kerakligini aniqla.
Mavjud agentlar: patients, services, statistic, users, laboratory

FAQAT JSON qaytardir, boshqa narsa yozma:
{"agents": [{"app": "app_nomi", "task": "bu agentga aniq vazifa"}]}""",
        messages=[{"role": "user", "content": main_task}]
    ))

    # JSON parse
    try:
        text = plan_response.content[0].text
        # JSON ni topish
        start = text.find('{')
        end = text.rfind('}') + 1
        plan = json.loads(text[start:end])
        assignments = plan["agents"]
    except Exception as e:
        print(f"❌ Planner xatosi: {e}")
        print(f"Raw: {plan_response.content[0].text}")
        return

    print(f"✅ {len(assignments)} ta agent tayinlandi:")
    for a in assignments:
        print(f"   • [{a['app']}]: {a['task'][:60]}...")

    # 2. Barcha agentlar PARALLEL ishlaydi
    print(f"\n🚀 Agentlar parallel ishlamoqda...\n")
    results = await asyncio.gather(*[
        worker_agent(a["app"], a["task"])
        for a in assignments
    ])

    # 3. Natijalarni ko'rsatish
    print(f"\n{'='*60}")
    print("📊 NATIJALAR:")
    print(f"{'='*60}\n")

    for result in results:
        print(f"━━━ [{result['app'].upper()}] ━━━")
        print(result['result'])
        print()

    return results

# ─── MISOL VAZIFALAR ──────────────────────────────────────────────────────────

EXAMPLE_TASKS = [
    # 1. Oddiy vazifa — bitta agent
    "patients app da bemor qidirish formasi uchun AJAX endpoint yoz",

    # 2. Ko'p agent vazifa
    "Bemorga xizmat qo'shishda shifokor o'z sevimli xizmatlar paketini saqlash "
    "va keyingi bemorlarga tez qo'shish imkoniyatini bering. "
    "Statistikada paket bo'yicha hisobot ham chiqsin.",

    # 3. Murakkab vazifa
    "Lab natijalari kiritilganda bemor telegramga xabar olsin, "
    "statistikada lab hisoboti chiqsin"
]

# ─── ISHGA TUSHIRISH ──────────────────────────────────────────────────────────

async def main():
    print("SKB_STAT Multi-Agent Tizimi")
    print("="*60)
    print("Mavjud agentlar:", ", ".join(AGENTS.keys()))
    print("="*60)
    print("\nMisol vazifalar:")
    for i, task in enumerate(EXAMPLE_TASKS, 1):
        print(f"{i}. {task[:70]}...")

    print("\nVazifangizni kiriting (yoki 1-3 raqam misol uchun):")
    user_input = input("> ").strip()

    if user_input in ["1", "2", "3"]:
        task = EXAMPLE_TASKS[int(user_input) - 1]
    else:
        task = user_input

    if task:
        await orchestrator(task)

if __name__ == "__main__":
    asyncio.run(main())
