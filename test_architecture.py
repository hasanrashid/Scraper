#!/usr/bin/env python3
"""
Test script to verify the new architecture works correctly
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Core.application import ApplicationFactory

def test_basic_functionality():
    """Test basic functionality of the new architecture"""
    
    print("Testing new scraper architecture...")
    
    try:
        # Create production app
        print("1. Creating production application...")
        app = ApplicationFactory.create_production_app()
        
        print("   ✓ Application created successfully")
        print(f"   ✓ Supported hosts: {app.get_supported_hosts()}")
        
        # Test configuration access
        print("2. Testing configuration access...")
        config = app.config
        print(f"   ✓ User agent: {config.get_user_agent()}")
        print(f"   ✓ Download folder: {config.get_download_folder()}")
        
        # Test scraper creation
        print("3. Testing scraper functionality...")
        scraper = app.get_scraper()
        print("   ✓ Scraper instance created")
        
        # Test download orchestrator
        print("4. Testing download orchestrator...")
        downloader = app.get_downloader()
        print("   ✓ Download orchestrator created")
        
        # Clean up
        app.close()
        print("   ✓ Application closed successfully")
        
        print("\\n✅ All basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_dependency_injection():
    """Test that dependency injection works correctly"""
    
    print("\\nTesting dependency injection...")
    
    try:
        # Create test app with mocks
        print("1. Creating test application with mocks...")
        app = ApplicationFactory.create_test_app()
        
        print("   ✓ Test application created")
        print("   ✓ Mock dependencies injected")
        
        # Verify we're using test configuration
        config = app.config
        assert config.get_user_agent() == 'Mozilla/5.0 (Test) TestAgent/1.0'
        assert '/tmp/test-downloads' in config.get_download_folder()
        
        print("   ✓ Test configuration verified")
        
        app.close()
        print("\\n✅ Dependency injection tests passed!")
        return True
        
    except Exception as e:
        print(f"\\n❌ Dependency injection test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    
    print("=" * 60)
    print("SCRAPER ARCHITECTURE VERIFICATION")
    print("=" * 60)
    
    success = True
    
    # Run basic functionality tests
    if not test_basic_functionality():
        success = False
    
    # Run dependency injection tests
    if not test_dependency_injection():
        success = False
    
    print("\\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED - New architecture is working!")
    else:
        print("💥 SOME TESTS FAILED - Check the errors above")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())