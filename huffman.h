#ifndef HUFFMAN_H
#define HUFFMAN_H

#include <stdio.h>
#include <stdlib.h>

// 定义哈夫曼树节点
typedef struct Node {
    unsigned char data;  // 使用 unsigned char 处理 0-255 的字符
    unsigned freq;       // 出现频率
    struct Node *left, *right;
} Node;

// 函数声明
Node* createNode(unsigned char data, unsigned freq);
void countFrequency(const char* filename, unsigned f[256]);

#endif