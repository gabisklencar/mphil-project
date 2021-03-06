/*
 * RUN: clang %cflags -emit-llvm -S %s -o %t.ll
 * RUN: soaap -o %t.soaap.ll %t.ll > %t.out
 * RUN: FileCheck %s -input-file %t.out
 *
 * CHECK: Running Soaap Pass
 */
#include "soaap.h"
#include <string.h>

int sensitive __soaap_classify("secret");

void dostuff();

int main() {
  sensitive = 25;
  dostuff();
  return 0;
}

__soaap_sandbox_persistent("foo")
//__soaap_clearance("secret")
void dostuff() {
  /*
   * CHECK: *** Sandboxed method "dostuff" read
   * CHECK:     data value of class: [secret] but
   * CHECK:     only has clearances for: []
   */
  int y = sensitive;
  printf("secret y is: %d\n", y);
}
