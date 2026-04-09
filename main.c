//程序的入口 处理用户输入
#include <stdio.h>
#include "huffman.h"

int main() {
    printf("--- 哈夫曼文件压缩器 ---\n");
    
    unsigned freq[256];
    char filename[] = "test.txt"; // 你可以在项目根目录建一个 test.txt 写点东西进去

    countFrequency(filename, freq);

    printf("字符频率统计结果 (部分):\n");
    for (int i = 0; i < 256; i++) {
        if (freq[i] > 0) {
            printf("字符 '%c' (ASCII %d): 出现 %u 次\n", i, i, freq[i]);
        }
    }

    return 0;
}