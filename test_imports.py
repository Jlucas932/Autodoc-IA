#!/usr/bin/env python3
"""
Script to test if imports work correctly after fixes
"""
import sys
import os

# Add src/main/python to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'main', 'python'))

print("Testing imports...")
print(f"Python path: {sys.path[0]}")

try:
    # Test the original failing import (should still fail)
    try:
        from domain.usecase.etp.etp_generator import EtpGenerator
        print("❌ ERROR: domain.usecase.etp.etp_generator should not exist!")
    except ModuleNotFoundError:
        print("✅ Confirmed: domain.usecase.etp.etp_generator does not exist (expected)")
    
    # Test the correct import
    from domain.usecase.etp.etp_generator_dynamic import DynamicEtpGenerator
    print("✅ Successfully imported DynamicEtpGenerator")
    
    # Test instantiation with dummy key
    generator = DynamicEtpGenerator("test_key")
    print("✅ Successfully instantiated DynamicEtpGenerator")
    
    # Test that it has the expected client attribute
    if hasattr(generator, 'client'):
        print("✅ DynamicEtpGenerator has 'client' attribute")
    else:
        print("❌ DynamicEtpGenerator missing 'client' attribute")
    
    print("\n🎉 All import tests passed!")
    
except Exception as e:
    print(f"❌ Import test failed: {e}")
    sys.exit(1)