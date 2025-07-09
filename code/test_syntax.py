#!/usr/bin/env python3
"""
Simple test to verify main_email_fetch.py syntax is fixed
"""

def test_syntax():
    """Test that main_email_fetch.py compiles without syntax errors"""
    try:
        import py_compile
        py_compile.compile('main_email_fetch.py', doraise=True)
        print("✅ main_email_fetch.py syntax is valid")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax error in main_email_fetch.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error compiling main_email_fetch.py: {e}")
        return False

if __name__ == "__main__":
    test_syntax()
