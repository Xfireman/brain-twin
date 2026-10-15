"""Executable UI invariants; deliberately invalid inputs prove the checks can fail."""
from pathlib import Path
import re
import pytest
ROOT=Path(__file__).parents[1]/'brain_twin'


def violations(source):
    failures=[]
    if re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(',source):failures.append('literal color')
    if re.search(r'\b100vh\b',source):failures.append('mobile viewport')
    if re.search(r'transition\s*:\s*all\b',source):failures.append('layout animation')
    if re.search(r'(?:div|span)\b[^>]*onclick\s*=',source):failures.append('non-button interaction')
    return failures


def test_components_use_tokens_and_safe_interaction():
    failures=[]
    for folder in ('templates','static'):
        for path in (ROOT/folder).glob('*'):
            if path.suffix in ('.html','.css','.js') and path.name!='tokens.css':
                failures.extend(f'{path.name}: {v}' for v in violations(path.read_text()))
    assert not failures,failures


@pytest.mark.parametrize('bad',['.x{color:#fff}','.x{background:var(--bt-bg,#000)}','.x{height:100vh}','.x{transition:all 1s}','<div onclick="go()">'])
def test_design_checks_reject_counterexamples(bad):
    assert violations(bad)


def rgb(value):return [int(value[i:i+2],16)/255 for i in (1,3,5)]
def luminance(value):
    linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb(value)]
    return sum(x*y for x,y in zip(linear,(.2126,.7152,.0722)))
def contrast(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)


def test_both_theme_text_and_buttons_have_contrast():
    css=(ROOT/'static/tokens.css').read_text()
    light,dark=css.split('[data-theme="dark"]',1)
    values={}
    for theme,body in [('light',light),('dark',dark)]:
        values.update(dict(re.findall(r'--bt-([\w-]+):\s*(#[a-fA-F0-9]{6})',body)))
        for surface in ('surface','surface-2','bg','surface-3'):
            for text in ('text','text-2','text-3','primary-text'):
                assert contrast(values[text],values[surface])>=4.5,(theme,text,surface)
        # Primary and hovered primary carry button text, rather than being decoration.
        for button in ('primary','primary-hover'):
            assert contrast(values['on-primary'],values[button])>=4.5,(theme,button)


def test_contrast_checker_detects_unreadable_pair():
    assert contrast('#ffffff','#ffffff')<4.5
    assert contrast('#000000','#ffffff')>20
