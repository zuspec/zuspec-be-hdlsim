"""Test HDLTestbench checker."""
import pytest
import zuspec.dataclasses as zdc
from zuspec.be.hdlsim.checker import HDLTestbenchChecker


def test_checker_can_be_created():
    """Verify checker can be instantiated."""
    checker = HDLTestbenchChecker()
    assert checker is not None


def test_checker_identifies_extern_component(extern_component):
    """Verify checker identifies Extern components as SV."""
    checker = HDLTestbenchChecker()
    checker.check_component(extern_component)
    
    assert extern_component.__name__ in checker._sv_components
    assert extern_component.__name__ not in checker._py_components


def test_checker_identifies_xtor_component(xtor_component):
    """Verify checker identifies XtorComponent as SV."""
    checker = HDLTestbenchChecker()
    checker.check_component(xtor_component)
    
    assert xtor_component.__name__ in checker._sv_components
    assert xtor_component.__name__ not in checker._py_components


def test_checker_identifies_python_component(simple_component):
    """Verify checker identifies regular Component as Python."""
    checker = HDLTestbenchChecker()
    checker.check_component(simple_component)
    
    assert simple_component.__name__ in checker._py_components
    assert simple_component.__name__ not in checker._sv_components


def test_checker_has_no_errors_initially():
    """Verify checker starts with no errors."""
    checker = HDLTestbenchChecker()
    
    assert not checker.has_errors()
    assert len(checker.get_errors()) == 0


def test_checker_validates_bindings(xtor_component):
    """Verify checker validates __bind__ method."""
    checker = HDLTestbenchChecker()
    checker.check_component(xtor_component)
    
    # Should not have errors for valid component
    assert not checker.has_errors()


def test_checker_integration_with_profile():
    """Verify checker integrates with profile."""
    from zuspec.be.hdlsim.profile import HDLTestbenchProfile
    
    checker = HDLTestbenchProfile.get_checker()
    assert isinstance(checker, HDLTestbenchChecker)
