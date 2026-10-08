"""Brace motorunun yapı aşaması: fonksiyon / sınıf / karmaşıklık / içe aktarma.

Beklenen değerler örnek kod üzerinde elle sayılmıştır. Sonuçlar yaklaşıktır; kapsam dışı bilinen sınırlar
dosyanın sonunda belgelenmiştir.
"""
import pytest

from src.languages import default_languages


def analyze(language_id, source):
    return default_languages.get(language_id).analyze(source)


def funcs(m):
    return [(f.name, f.complexity, f.start_line, f.end_line) for f in m.functions]


def classes(m):
    return [(c.name, c.method_count, c.start_line, c.end_line) for c in m.classes]


CSHARP = r'''using System;
using System.Collections.Generic;
using static System.Math;
namespace Demo {
    // yorum { bozmasın
    [Serializable]
    public class Order : IEntity {
        private readonly string text = "{ not a brace } // nor comment";
        public int Id { get; set; }
        [Fact]
        public void Process(int a, int b) {
            if (a > 0 && b > 0) {
                foreach (var x in items) { total += x; }
            } else if (a < 0 || b < 0) {
                return;
            }
            var v = a > b ? a : b;
            int? n = null;
            var s = $"val {a}";
            var t = @"C:\path\{x}";
        }
        public Order(int id) : base() { Id = id; }
        public async Task<int> Run() { using (var c = new Conn()) { return 1; } }
    }
    public record Person(string Name) { public void Hi() { } }
    public struct P { public int X; }
    enum Color { Red, Green }
}
'''


def test_csharp():
    m = analyze("csharp", CSHARP)
    assert m.imports == ["System", "System.Collections.Generic", "System.Math"]
    assert classes(m) == [("Order", 3, 7, 24), ("Person", 1, 25, 25), ("P", 0, 26, 26)]   # enum sınıf sayılmaz
    assert funcs(m) == [("Process", 7, 11, 21), ("Order", 1, 22, 22), ("Run", 1, 23, 23), ("Hi", 1, 25, 25)]
    assert m.parse_ok and m.approximate and m.language == "csharp"
    # Process: 1 + if + && + foreach + else if + || + üçlü = 7; `int?` ve `using (` sayılmaz


JAVA = r'''package a.b;
import java.util.List;
import static java.lang.Math.max;
import java.io.*;
/** javadoc { */
@Entity
public class Foo<T extends Comparable<T>> implements Bar {
    private String s = "}{";
    @Override
    @RequestMapping("/x")
    public <U> void run(List<? extends U> a) throws IOException {
        for (int i = 0; i < 3; i++) {
            if (i % 2 == 0) { continue; }
        }
        Runnable r = () -> { System.out.println("x"); };
        Object o = new Object() { public void anon() { } };
        switch (a.size()) { case 1: break; case 2: break; default: break; }
        try { work(); } catch (Exception e) { }
        String tb = """
            text { block
            """;
    }
    public Foo() { }
    interface Inner { void m(); }
}
'''


def test_java():
    m = analyze("java", JAVA)
    assert m.imports == ["java.util.List", "java.lang.Math.max", "java.io"]
    assert classes(m) == [("Foo", 2, 7, 25), ("Inner", 0, 24, 24)]
    # `new Object() {` fonksiyon sayılmaz, içindeki metot ise ayrı bir fonksiyondur ama Foo'nun metodu değildir
    assert funcs(m) == [("run", 6, 11, 22), ("anon", 1, 16, 16), ("Foo", 1, 23, 23)]
    # run: 1 + for + if + case + case + catch = 6; `List<? extends U>` ve lambda sayılmaz


C_SOURCE = r'''#include <stdio.h>
#include "local.h"
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define BLOCK { \
   do_it(); }
typedef struct node {
    int v;
    struct node *next;
} node_t;
struct node *make(int v) {
    struct node *n = malloc(sizeof(*n));
    if (!n) { return NULL; }
    char c = '{';
    n->v = v > 0 ? v : 0;
    return n;
}
static int count(node_t *h) {
    int n = 0;
    while (h && h->v) { n++; h = h->next; }
    for (;;) { break; }
    return n;
}
int arr[] = { 1, 2, 3 };
'''


def test_c():
    m = analyze("c", C_SOURCE)
    assert m.imports == ["stdio.h", "local.h"]
    assert classes(m) == [("node", 0, 6, 9)]          # satır devamlı #define satır sayısını bozmaz
    # `struct node *make(...) {` sınıf değil fonksiyon; `int arr[] = {` düz blok
    assert funcs(m) == [("make", 3, 10, 16), ("count", 4, 17, 22)]
    assert m.parse_ok


CPP = r'''#include <vector>
#include "x.hpp"
namespace ns {
template <typename T>
class Box : public Base<T> {
public:
    Box(int a) : a_(a), b_{0} { }
    ~Box() { }
    T get() const { return v; }
    void set(T x) { if (x) { v = x; } }
    bool operator==(const Box& o) const { return v == o.v; }
private:
    T v;
};
template<class T> void helper(T x) { for (auto& e : x) { if (e) {} } }
void Box::fn() { auto f = [](int q) { return q > 0 && q < 5; }; }
const char* raw = R"delim(} { // not code)delim";
int big = 1'000'000;
}
'''


def test_cpp():
    m = analyze("cpp", CPP)
    assert m.imports == ["vector", "x.hpp"]
    assert [(n, k) for n, k, *_ in classes(m)] == [("Box", 5)]            # template<class T> sınıf sayılmaz
    assert [(n, c) for n, c, *_ in funcs(m)] == [
        ("Box", 1), ("~Box", 1), ("get", 1), ("set", 2), ("operator==", 1), ("helper", 3), ("fn", 2)]
    assert m.parse_ok


JAVASCRIPT = r'''import React, { useState } from 'react';
import fs from "fs";
const lodash = require('lodash');
export { a } from './a';
// comment {
const re = /ab+c{2}[/]\//g;
const div = a / b / c;
function plain(a, b) {
  if (a && b) { return 1; }
  const t = `tpl ${a} { }`;
  return a ? b : c;
}
const arrow = async (x) => {
  for (const i of x) { if (i) { continue; } }
};
const fnExpr = function named() { };
class Widget extends Base {
  constructor(props) { super(props); }
  render() { return <div>Don't {x}</div>; }
  static helper = () => { return 1; };
  async load() { await fetch('/x'); }
}
const obj = { method() { return 1; }, other: function() { } };
promise.then(res => { if (res) { done(); } });
'''


def test_javascript():
    m = analyze("javascript", JAVASCRIPT)
    assert m.imports == ["react", "fs", "lodash", "./a"]
    assert classes(m) == [("Widget", 4, 17, 22)]
    assert [(n, c) for n, c, *_ in funcs(m)] == [
        ("plain", 4), ("arrow", 3), ("named", 1), ("constructor", 1), ("render", 1),
        ("helper", 1), ("load", 1), ("method", 1), ("other", 1)]
    # `promise.then(res => {` parantez içinde: ayrı fonksiyon değil, karmaşıklığı ana bloğa gider
    assert m.parse_ok


TYPESCRIPT = r'''import { Injectable } from '@angular/core';
import type { Foo } from "./foo";
@Injectable({ providedIn: 'root' })
export class Svc implements OnInit {
  private x?: number;
  constructor(private http: HttpClient) {}
  @HostListener('window:resize') onResize(e: Event): void { if (e) {} }
  async get<T>(id: number): Promise<T | null> { return a ?? b; }
}
export interface Shape { area(): number; }
export default function util<T>(a: T): T { return a; }
const f = (a: number, b = 2): number => { return a > b ? a : b; };
'''


def test_typescript():
    m = analyze("typescript", TYPESCRIPT)
    assert m.imports == ["@angular/core", "./foo"]
    assert [(n, k) for n, k, *_ in classes(m)] == [("Svc", 3), ("Shape", 0)]
    assert [(n, c) for n, c, *_ in funcs(m)] == [
        ("constructor", 1), ("onResize", 2), ("get", 1), ("util", 1), ("f", 2)]
    # `a ?? b` ve isteğe bağlı alan `x?:` karar sayılmaz


GO = r'''package main

import (
	"fmt"
	str "strings"
	_ "github.com/lib/pq"
)
import "os"

type Server struct { name string }

// Start runs { it
func (s *Server) Start(port int) error {
	if port > 0 && port < 65535 {
		for i := 0; i < 3; i++ {
			select { case <-done: return nil; default: }
		}
	}
	f := func() { fmt.Println("x") }
	f()
	return nil
}
func helper[T any](x T) T { return x }
func main() { var raw = `}{` ; _ = raw }
'''


def test_go():
    m = analyze("go", GO)
    assert sorted(m.imports) == ["fmt", "github.com/lib/pq", "os", "strings"]
    assert m.classes == []
    assert [(n, c) for n, c, *_ in funcs(m)] == [("Start", 5), ("helper", 1), ("main", 1)]   # `f := func() {` ayrı değil
    assert m.parse_ok


RUST = r'''use std::collections::HashMap;
use serde::{Serialize, Deserialize};
extern crate rand;
pub struct Counter { n: u32 }
impl<T: Display> Wrapper<T> where T: Clone {
    pub fn new(v: T) -> Self { Wrapper { v } }
    fn go<'a>(&self, s: &'a str) -> &'a str {
        let c = 'x';
        match s.len() { 0 => "", 1 => "a", _ => s }
    }
}
impl Trait for Counter {
    fn tick(&mut self) -> bool { if self.n > 3 && self.n < 9 || self.n == 0 { true } else { false } }
}
fn free() -> impl Iterator<Item = u8> { (0..3).map(|x| x) }
let raw = r#"} { "quoted""#;
'''


def test_rust():
    m = analyze("rust", RUST)
    assert m.imports == ["std::collections::HashMap", "serde", "rand"]
    assert [(n, k) for n, k, *_ in classes(m)] == [("Counter", 0), ("Wrapper", 2), ("Counter", 1)]
    assert [(n, c) for n, c, *_ in funcs(m)] == [("new", 1), ("go", 4), ("tick", 4), ("free", 1)]
    # `-> impl Iterator {` fonksiyondur (impl bloğu değil); go: 1 + 3 kol; tick: 1 + if + && + ||


# ---- yönlendirme ve dayanıklılık --------------------------------------------------------

def test_header_file_is_c_unless_it_looks_like_cpp():
    c_lang = default_languages.for_extension(".h")
    assert c_lang.refine("int f(void);\nstruct s { int a; };\n") == "c"
    assert c_lang.refine("namespace x {\nclass A;\n}\n") == "cpp"
    assert c_lang.refine("template <typename T>\nstruct S {};\n") == "cpp"
    assert c_lang.refine("#include <vector>\nstd::vector<int> v;\n") == "cpp"


def test_unbalanced_braces_mark_parse_not_ok_and_drop_unclosed_blocks():
    m = analyze("java", "class A {\n  void f() {\n    if (x) {\n")
    assert m.parse_ok is False
    assert m.functions == [] and m.classes == []          # kapanmayan bloklardan sahte uzun sınıf üretilmez


def test_extra_closing_brace_marks_parse_not_ok():
    m = analyze("c", "int f(void) { return 1; }\n}\n")
    assert m.parse_ok is False
    assert [f.name for f in m.functions] == ["f"]


def test_empty_and_comment_only_files():
    m = analyze("typescript", "// yalnızca yorum\n/* ve blok */\n")
    assert (m.total_lines, m.comment_lines, m.code_lines) == (2, 2, 0)
    assert m.functions == [] and m.classes == [] and m.imports == []


def test_control_keywords_are_never_functions():
    src = "void f() {\n  if (a) { }\n  else if (b) { }\n  while (c) { }\n  switch (d) { }\n  for (;;) { }\n}\n"
    assert [f.name for f in analyze("c", src).functions] == ["f"]
    src_js = "function g() {\n  if (a) { }\n  catch (e) { }\n  switch (x) { }\n}\n"
    assert [f.name for f in analyze("javascript", src_js).functions] == ["g"]


def test_nested_function_complexity_counts_in_parent_like_python():
    src = "function outer() {\n  if (a) {}\n  function inner() { if (b) {} }\n}\n"
    result = {f.name: f.complexity for f in analyze("javascript", src).functions}
    assert result == {"outer": 3, "inner": 2}


@pytest.mark.parametrize("language_id,source", [
    ("c", "int main(void) {\n  return 0;\n}\n"),
    ("go", "func main() {\n}\n"),
    ("rust", "fn main() {\n}\n"),
    ("java", "class A { void m() {} }\n"),
])
def test_function_line_range_and_length(language_id, source):
    m = analyze(language_id, source)
    main = next(f for f in m.functions)
    assert main.start_line >= 1 and main.end_line >= main.start_line and main.lines == main.end_line - main.start_line + 1


# Bilinen sınırlar (yaklaşık çözümleyici, bilerek kapsam dışı):
#  - Fonksiyon benzeri makrolar (`FOREACH(x) {`) C/C++ içinde fonksiyon sanılabilir.
#  - Template literal içindeki iç içe `${ `}` }` kalıpları string bitişini bozabilir.
#  - Rust'ta iç içe blok yorumları (`/* /* */ */`) desteklenmez.
#  - C#/Java'da `=>`/`->` ile yazılmış ifade gövdeli üyeler (süslü parantezsiz) fonksiyon sayılmaz.
