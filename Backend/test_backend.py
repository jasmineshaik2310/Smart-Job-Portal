# test_backend.py
print("=" * 50)
print("Testing SmartJob Portal Backend Imports")
print("=" * 50)

# Test each import
imports_to_test = [
    ("fastapi", "FastAPI"),
    ("pymongo", "MongoClient"),
    ("PyPDF2", "PdfReader"),
    ("docx2txt", "process"),
    ("pandas", "pd"),
    ("jose", "JWT"),
    ("passlib", "CryptContext"),
    ("dotenv", "load_dotenv")
]

success_count = 0
for module_name, attr_name in imports_to_test:
    try:
        if module_name == "pandas":
            import pandas as pd
            print(f"✅ {module_name} {pd.__version__}")
        elif module_name == "jose":
            from jose import jwt
            print(f"✅ {module_name} (JWT support)")
        elif module_name == "passlib":
            from passlib.context import CryptContext
            print(f"✅ {module_name}")
        else:
            module = __import__(module_name)
            if hasattr(module, attr_name):
                print(f"✅ {module_name}")
            else:
                print(f"⚠️ {module_name} imported but {attr_name} not found")
        success_count += 1
    except ImportError as e:
        print(f"❌ {module_name} failed: {e}")

print(f"\n✅ Successfully imported {success_count}/{len(imports_to_test)} packages")

if success_count == len(imports_to_test):
    print("\n🎉 All imports successful! You can now run the backend.")
    print("Run: uvicorn main:app --reload")
else:
    print("\n⚠️ Some packages are missing. Run:")
    print("pip install pandas==2.0.3 numpy==1.24.3")
    print("pip install pydantic==2.5.3 pydantic-settings email-validator")