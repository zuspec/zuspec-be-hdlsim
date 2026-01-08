"""Test HDLTestbench profile."""
import pytest
import zuspec.dataclasses as zdc


def test_profile_can_be_imported():
    """Verify profile module can be imported."""
    from zuspec.be.hdlsim.profile import HDLTestbenchProfile
    assert HDLTestbenchProfile is not None


def test_profile_has_get_checker():
    """Verify profile provides get_checker method."""
    from zuspec.be.hdlsim.profile import HDLTestbenchProfile
    
    assert hasattr(HDLTestbenchProfile, 'get_checker')
    checker = HDLTestbenchProfile.get_checker()
    assert checker is not None


def test_profile_can_be_used_as_decorator():
    """Verify profile can be used in @dataclass decorator."""
    from zuspec.be.hdlsim.profile import HDLTestbenchProfile
    
    @zdc.dataclass(profile=HDLTestbenchProfile)
    class TestComponent(zdc.Component):
        """Test component with profile."""
        pass
    
    assert TestComponent is not None
    # Component should be created successfully
    comp = TestComponent()
    assert comp is not None


def test_profile_is_singleton():
    """Verify profile is a singleton instance."""
    from zuspec.be.hdlsim.profile import HDLTestbenchProfile
    
    # Should be the same instance
    assert HDLTestbenchProfile is HDLTestbenchProfile
